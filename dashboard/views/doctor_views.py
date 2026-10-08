"""
Custom dashboard views for Doctor management.

Handles:
  - Doctor list (search, filter, pagination)
  - Doctor create (with multiple specialists + multiple chamber schedules)
  - Doctor edit
  - Doctor delete
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count, Prefetch
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

    # Search
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

    # Filter by specialist
    specialist_id = request.GET.get("specialist", "").strip()
    if specialist_id:
        qs = qs.filter(specialists__id=specialist_id)

    # Filter by status
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

    # Sort
    sort = request.GET.get("sort", "-created_at").strip()
    allowed_sorts = {
        "name": "name_en",
        "-name": "-name_en",
        "newest": "-created_at",
        "oldest": "created_at",
        "updated": "-updated_at",
    }
    qs = qs.order_by(allowed_sorts.get(sort, "-created_at"))

    # Pagination
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # KPI counts
    total = Doctor.objects.count()
    active_count = Doctor.objects.filter(is_active=True).count()
    verified_count = Doctor.objects.filter(is_verified=True).count()
    featured_count = Doctor.objects.filter(is_featured=True).count()

    # For filter dropdown
    specialists = Specialist.objects.filter(is_active=True).order_by("name_en")

    context = {
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "sort": sort,
        "specialist_id": specialist_id,
        "specialists": specialists,
        "total": total,
        "active_count": active_count,
        "verified_count": verified_count,
        "featured_count": featured_count,
        "page_title": "Doctors",
    }
    return render(request, "dashboard/doctor_list.html", context)


# ==================================================================
# CREATE / EDIT (same form)
# ==================================================================
@staff_member_required
def doctor_create(request):
    return _doctor_form(request, doctor=None)


@staff_member_required
def doctor_edit(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    return _doctor_form(request, doctor=doctor)


def _doctor_form(request, doctor):
    """Shared logic for create/edit."""
    is_edit = doctor is not None

    # Get all active specialists and centers for form
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
                "page_title": f"Edit: {doctor.name_en}" if is_edit else "New Doctor",
            })

        # Save inside transaction
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

            # Set specialists (M2M)
            specialist_ids = request.POST.getlist("specialists")
            doctor.specialists.set(Specialist.objects.filter(id__in=specialist_ids))

            # Create chambers
            chambers_data = _extract_chambers_data(request)
            for ch in chambers_data:
                if not ch.get("diagnostic_center_id"):
                    continue  # skip empty rows
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
        messages.success(request, f'"{doctor.name_bn}" {action} successfully.')
        return redirect("dashboard:doctor_list")

    # GET: populate form_data
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
        # Format time for HTML input type="time"
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
        "page_title": f"Edit: {doctor.name_en}" if is_edit else "New Doctor",
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
    messages.success(request, f'"{name}" deleted.')
    return redirect("dashboard:doctor_list")


# ==================================================================
# HELPERS
# ==================================================================
def _extract_doctor_data(request):
    post = request.POST
    errors = []

    name_bn = (post.get("name_bn") or "").strip()
    name_en = (post.get("name_en") or "").strip()

    if not name_bn:
        errors.append("Bangla name is required.")
    if not name_en:
        errors.append("English name is required.")

    # experience_years validation
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
    Chambers come as parallel arrays:
      center_ids[], days[], start_times[], end_times[], rooms[], phones[]
    Returns a list of dicts.
    """
    post = request.POST
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

        # Skip fully empty rows
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