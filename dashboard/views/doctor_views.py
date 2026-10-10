"""
Custom dashboard views for Doctor management.

Handles:
  - Doctor list (search, filter, pagination)
  - Doctor create via AJAX (with multiple specialists + multi-day chamber schedules)
  - Doctor create/edit via full page (fallback)
  - Doctor delete
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from doctors.models import Doctor, Specialist, DiagnosticCenter, Chamber, Weekday


# ==================================================================
# LIST
# ==================================================================
@staff_member_required
def doctor_list(request):
    """Display all doctors with search / filter / pagination."""
    qs = (
        Doctor.objects
        .prefetch_related("specialists")
        .annotate(chamber_count=Count("chambers", distinct=True))
    )

    # ---- Search ----
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(name_bn__icontains=q)
            | Q(name_en__icontains=q)
            | Q(phone__icontains=q)
            | Q(bmdc_reg_no__icontains=q)
            | Q(qualification_bn__icontains=q)
            | Q(qualification_en__icontains=q)
            | Q(specialists__name_bn__icontains=q)
            | Q(specialists__name_en__icontains=q)
        ).distinct()

    # ---- Filter by specialist ----
    specialist_id = request.GET.get("specialist", "").strip()
    if specialist_id:
        qs = qs.filter(specialists__id=specialist_id)

    # ---- Filter by status ----
    status = request.GET.get("status", "").strip()
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)
    elif status == "verified":
        qs = qs.filter(is_verified=True)
    elif status == "unverified":
        qs = qs.filter(is_verified=False)
    elif status == "featured":
        qs = qs.filter(is_featured=True)

    # ---- Sort ----
    sort = request.GET.get("sort", "-created_at").strip()
    allowed_sorts = {
        "name": "name_en",
        "-name": "-name_en",
        "newest": "-created_at",
        "oldest": "created_at",
        "updated": "-updated_at",
    }
    qs = qs.order_by(allowed_sorts.get(sort, "-created_at"))

    # ---- Pagination ----
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # ---- KPI counts ----
    total = Doctor.objects.count()
    active_count = Doctor.objects.filter(is_active=True).count()
    verified_count = Doctor.objects.filter(is_verified=True).count()
    featured_count = Doctor.objects.filter(is_featured=True).count()

    # ---- Context for filters AND modals ----
    specialists = Specialist.objects.filter(is_active=True).order_by("display_order", "name_en")
    centers = DiagnosticCenter.objects.filter(is_active=True).order_by("name_en")
    weekdays = Weekday.choices

    context = {
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "sort": sort,
        "specialist_id": specialist_id,
        "specialists": specialists,
        "centers": centers,           # needed by chamber picker modal
        "weekdays": weekdays,         # needed by chamber picker modal
        "total": total,
        "active_count": active_count,
        "verified_count": verified_count,
        "featured_count": featured_count,
        "page_title": "Doctors",
    }
    return render(request, "dashboard/doctor_list.html", context)


# ==================================================================
# CREATE (full-page fallback)
# ==================================================================
@staff_member_required
def doctor_create(request):
    return _doctor_form(request, doctor=None)


# ==================================================================
# CREATE (AJAX — used by modal)
# ==================================================================
@staff_member_required
@require_POST
def doctor_create_ajax(request):
    """
    Create a new doctor via AJAX (from the modal on the list page).
    Handles: basic info + specialists (M2M) + chambers (multi-day).
    """
    data, errors = _extract_doctor_data(request)

    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    with transaction.atomic():
        doctor = Doctor(**data)
        if request.FILES.get("photo"):
            doctor.photo = request.FILES["photo"]
        doctor.save()

        # Specialists (M2M)
        specialist_ids = request.POST.getlist("specialists")
        if specialist_ids:
            doctor.specialists.set(Specialist.objects.filter(id__in=specialist_ids))

        # Chambers
        chambers_data = _extract_chambers_data(request)
        for ch in chambers_data:
            if not ch.get("diagnostic_center_id"):
                continue
            Chamber.objects.create(
                doctor=doctor,
                diagnostic_center_id=ch["diagnostic_center_id"],
                day=ch["day"],
                start_time=ch["start_time"],
                end_time=ch["end_time"],
                room_no=ch.get("room_no", ""),
                appointment_phone=ch.get("appointment_phone", ""),
                is_active=True,
            )

    return JsonResponse({
        "ok": True,
        "id": doctor.pk,
        "name_bn": doctor.name_bn,
        "name_en": doctor.name_en,
        "slug": doctor.slug,
        "message": '"' + doctor.name_bn + '" added successfully.',
    })


# ==================================================================
# EDIT (full page)
# ==================================================================
@staff_member_required
def doctor_edit(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    return _doctor_form(request, doctor=doctor)


def _doctor_form(request, doctor):
    """Shared logic for full-page create/edit."""
    is_edit = doctor is not None

    specialists = Specialist.objects.filter(is_active=True).order_by("display_order", "name_en")
    centers = DiagnosticCenter.objects.filter(is_active=True).order_by("name_en")
    weekdays = Weekday.choices

    if request.method == "POST":
        data, errors = _extract_doctor_data(request)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "dashboard/doctor_form.html", {
                "form_data": data,
                "chambers_data": _extract_chambers_data(request),
                "specialists": specialists,
                "centers": centers,
                "weekdays": weekdays,
                "selected_specialists": request.POST.getlist("specialists"),
                "mode": "edit" if is_edit else "create",
                "doctor": doctor,
                "page_title": ("Edit: " + doctor.name_en) if is_edit else "New Doctor",
            })

        with transaction.atomic():
            if is_edit:
                for field, value in data.items():
                    setattr(doctor, field, value)
                if request.FILES.get("photo"):
                    doctor.photo = request.FILES["photo"]
                doctor.save()

                # Replace chambers: delete all, re-create
                doctor.chambers.all().delete()
            else:
                doctor = Doctor(**data)
                if request.FILES.get("photo"):
                    doctor.photo = request.FILES["photo"]
                doctor.save()

            # Specialists
            specialist_ids = request.POST.getlist("specialists")
            if specialist_ids:
                doctor.specialists.set(Specialist.objects.filter(id__in=specialist_ids))

            # Chambers
            chambers_data = _extract_chambers_data(request)
            for ch in chambers_data:
                if not ch.get("diagnostic_center_id"):
                    continue
                Chamber.objects.create(
                    doctor=doctor,
                    diagnostic_center_id=ch["diagnostic_center_id"],
                    day=ch["day"],
                    start_time=ch["start_time"],
                    end_time=ch["end_time"],
                    room_no=ch.get("room_no", ""),
                    appointment_phone=ch.get("appointment_phone", ""),
                    is_active=True,
                )

        action = "updated" if is_edit else "added"
        messages.success(request, '"' + doctor.name_bn + '" ' + action + ' successfully.')
        return redirect("dashboard:doctor_list")

    # GET
    if is_edit:
        form_data = {
            "name_bn": doctor.name_bn,
            "name_en": doctor.name_en,
            "slug": doctor.slug,
            "qualification_bn": doctor.qualification_bn,
            "qualification_en": doctor.qualification_en,
            "designation_bn": doctor.designation_bn,
            "designation_en": doctor.designation_en,
            "bio_bn": doctor.bio_bn,
            "bio_en": doctor.bio_en,
            "experience_years": doctor.experience_years,
            "phone": doctor.phone,
            "phone_alt": doctor.phone_alt,
            "email": doctor.email,
            "bmdc_reg_no": doctor.bmdc_reg_no,
            "is_active": doctor.is_active,
            "is_verified": doctor.is_verified,
            "is_featured": doctor.is_featured,
        }
        chambers_data = list(
            doctor.chambers
            .select_related("diagnostic_center")
            .order_by("day", "start_time")
            .values(
                "diagnostic_center_id",
                "day",
                "start_time",
                "end_time",
                "room_no",
                "appointment_phone",
            )
        )
        for ch in chambers_data:
            if ch["start_time"]:
                ch["start_time"] = ch["start_time"].strftime("%H:%M")
            if ch["end_time"]:
                ch["end_time"] = ch["end_time"].strftime("%H:%M")

        selected_specialists = [str(s.id) for s in doctor.specialists.all()]
    else:
        form_data = {"is_active": True, "experience_years": 0}
        chambers_data = []
        selected_specialists = []

    return render(request, "dashboard/doctor_form.html", {
        "form_data": form_data,
        "chambers_data": chambers_data,
        "specialists": specialists,
        "centers": centers,
        "weekdays": weekdays,
        "selected_specialists": selected_specialists,
        "mode": "edit" if is_edit else "create",
        "doctor": doctor,
        "page_title": ("Edit: " + doctor.name_en) if is_edit else "New Doctor",
    })


# ==================================================================
# DELETE
# ==================================================================
@staff_member_required
@require_POST
def doctor_delete(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    name = doctor.name_bn
    doctor.delete()  # cascades to chambers
    messages.success(request, '"' + name + '" deleted.')
    return redirect("dashboard:doctor_list")


# ==================================================================
# FORM DATA EXTRACTORS
# ==================================================================
def _extract_doctor_data(request):
    """Extract + validate doctor basic info from POST."""
    post = request.POST
    errors = []

    name_bn = (post.get("name_bn") or "").strip()
    name_en = (post.get("name_en") or "").strip()

    if not name_bn:
        errors.append("Bangla name is required.")
    if not name_en:
        errors.append("English name is required.")

    exp_raw = (post.get("experience_years") or "").strip()
    try:
        experience_years = int(exp_raw) if exp_raw else 0
        if experience_years < 0:
            experience_years = 0
    except ValueError:
        errors.append("Experience years must be a number.")
        experience_years = 0

    data = {
        "name_bn": name_bn,
        "name_en": name_en,
        "slug": (post.get("slug") or "").strip(),
        "qualification_bn": (post.get("qualification_bn") or "").strip(),
        "qualification_en": (post.get("qualification_en") or "").strip(),
        "designation_bn": (post.get("designation_bn") or "").strip(),
        "designation_en": (post.get("designation_en") or "").strip(),
        "bio_bn": (post.get("bio_bn") or "").strip(),
        "bio_en": (post.get("bio_en") or "").strip(),
        "experience_years": experience_years,
        "phone": (post.get("phone") or "").strip(),
        "phone_alt": (post.get("phone_alt") or "").strip(),
        "email": (post.get("email") or "").strip(),
        "bmdc_reg_no": (post.get("bmdc_reg_no") or "").strip(),
        "is_active": post.get("is_active") == "on",
        "is_verified": post.get("is_verified") == "on",
        "is_featured": post.get("is_featured") == "on",
    }

    return data, errors


def _extract_chambers_data(request):
    """
    Parse chambers from POST.

    The frontend MAY send either of two formats:

    LEGACY (single-day-per-row — used by edit page):
        chamber_center[]  = ["1", "1", "2"]
        chamber_day[]     = ["sat", "mon", "tue"]
        chamber_start[]   = ["16:00", "16:00", "17:00"]
        chamber_end[]     = ["20:00", "20:00", "21:00"]
        chamber_room[]    = ["302", "", ""]
        chamber_phone[]   = ["017...", "", ""]

    MULTI-DAY (used by list-page modal):
        chamber_center[]       = ["1"]
        chamber_days[]         = ["sat", "mon", "thu"]   # flat list of all days
        chamber_days_count[]   = ["3"]                   # how many days per block
        chamber_start[]        = ["16:00"]
        chamber_end[]          = ["20:00"]
        chamber_room[]         = ["302"]
        chamber_phone[]        = ["017..."]

    Strategy: detect from POST keys, delegate accordingly.
    """
    post = request.POST

    # Format B — multi-day checkbox modal
    if "chamber_days[]" in post or "chamber_days_count[]" in post:
        return _extract_chambers_multi_day(post)

    # Format A — legacy single-day rows
    return _extract_chambers_legacy(post)


def _extract_chambers_multi_day(post):
    """
    Parse 'multi-day' format. Each center block can produce multiple
    chamber rows (one per selected day).

    Data:
        chamber_center[]      flat list of center ids (one per block)
        chamber_days[]        flat list of day codes (sat, mon, ...)
        chamber_days_count[]  how many days belong to each block (parallel to centers)
        chamber_start[]       start time per block
        chamber_end[]         end time per block
        chamber_room[]        room per block
        chamber_phone[]       phone per block
    """
    center_ids = post.getlist("chamber_center[]")
    days_flat = post.getlist("chamber_days[]")
    days_count = post.getlist("chamber_days_count[]")
    start_times = post.getlist("chamber_start[]")
    end_times = post.getlist("chamber_end[]")
    rooms = post.getlist("chamber_room[]")
    phones = post.getlist("chamber_phone[]")

    chambers = []
    day_cursor = 0

    for i, center_id in enumerate(center_ids):
        center_id = (center_id or "").strip()
        start = (start_times[i] if i < len(start_times) else "").strip()
        end = (end_times[i] if i < len(end_times) else "").strip()
        room = (rooms[i] if i < len(rooms) else "").strip()
        phone = (phones[i] if i < len(phones) else "").strip()

        # Number of days for this block
        try:
            n = int(days_count[i]) if i < len(days_count) else 0
        except (ValueError, IndexError):
            n = 0

        block_days = days_flat[day_cursor:day_cursor + n]
        day_cursor += n

        if not center_id or not block_days:
            continue

        for day in block_days:
            day = (day or "").strip()
            if not day:
                continue
            chambers.append({
                "diagnostic_center_id": center_id,
                "day": day,
                "start_time": start,
                "end_time": end,
                "room_no": room,
                "appointment_phone": phone,
            })

    return chambers


def _extract_chambers_legacy(post):
    """Parse 'legacy' single-day-per-row format (parallel arrays)."""
    center_ids = post.getlist("chamber_center[]")
    days = post.getlist("chamber_day[]")
    start_times = post.getlist("chamber_start[]")
    end_times = post.getlist("chamber_end[]")
    rooms = post.getlist("chamber_room[]")
    phones = post.getlist("chamber_phone[]")

    chambers = []
    for i, center_id in enumerate(center_ids):
        center_id = (center_id or "").strip()
        day = (days[i] if i < len(days) else "").strip()
        start = (start_times[i] if i < len(start_times) else "").strip()
        end = (end_times[i] if i < len(end_times) else "").strip()
        room = (rooms[i] if i < len(rooms) else "").strip()
        phone = (phones[i] if i < len(phones) else "").strip()

        if not any([center_id, day, start, end]):
            continue

        chambers.append({
            "diagnostic_center_id": center_id or None,
            "day": day,
            "start_time": start,
            "end_time": end,
            "room_no": room,
            "appointment_phone": phone,
        })

    return chambers