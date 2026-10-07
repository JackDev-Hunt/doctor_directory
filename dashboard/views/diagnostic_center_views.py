"""
Custom dashboard views for Diagnostic Center management.

All views are staff-only (via @staff_member_required).
"""
import json

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from doctors.models import DiagnosticCenter


# ==================================================================
# LIST — with search, filter, pagination
# ==================================================================
@staff_member_required
def center_list(request):
    """Display all diagnostic centers with search / filter / pagination."""
    qs = DiagnosticCenter.objects.all().annotate(
        doctor_count=Count("chambers__doctor", distinct=True)
    )

    # Search
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(name_bn__icontains=q)
            | Q(name_en__icontains=q)
            | Q(area_bn__icontains=q)
            | Q(area_en__icontains=q)
            | Q(phone__icontains=q)
            | Q(address_bn__icontains=q)
            | Q(address_en__icontains=q)
        )

    # Filters
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
    total = DiagnosticCenter.objects.count()
    active_count = DiagnosticCenter.objects.filter(is_active=True).count()
    verified_count = DiagnosticCenter.objects.filter(is_verified=True).count()
    featured_count = DiagnosticCenter.objects.filter(is_featured=True).count()

    context = {
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "sort": sort,
        "total": total,
        "active_count": active_count,
        "verified_count": verified_count,
        "featured_count": featured_count,
        "page_title": "ডায়াগনস্টিক সেন্টার",
    }
    return render(request, "dashboard/diagnostic_center.html", context)


# ==================================================================
# CREATE (full page — fallback)
# ==================================================================
@staff_member_required
def center_create(request):
    """Create a new diagnostic center (full page form)."""
    if request.method == "POST":
        data, errors = _extract_center_data(request)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "dashboard/diagnostic_center_form.html", {
                "form_data": data,
                "mode": "create",
                "page_title": "নতুন ডায়াগনস্টিক সেন্টার",
            })

        center = DiagnosticCenter(**data)
        if request.FILES.get("logo"):
            center.logo = request.FILES["logo"]
        if request.FILES.get("cover"):
            center.cover = request.FILES["cover"]
        center.save()

        messages.success(request, f'"{center.name_bn}" সফলভাবে যোগ করা হয়েছে।')
        return redirect("dashboard:center_list")

    # GET
    return render(request, "dashboard/diagnostic_center_form.html", {
        "mode": "create",
        "page_title": "নতুন ডায়াগনস্টিক সেন্টার",
        "form_data": {"is_active": True},
    })


# ==================================================================
# CREATE (AJAX — used by modal on list page)
# ==================================================================
@staff_member_required
@require_POST
def center_create_ajax(request):
    """
    Create a new diagnostic center via AJAX (from modal).
    Returns JSON: {ok: true, id, name_bn, redirect: url} or {ok: false, errors: [...]}
    """
    data, errors = _extract_center_data(request)

    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    center = DiagnosticCenter(**data)
    if request.FILES.get("logo"):
        center.logo = request.FILES["logo"]
    if request.FILES.get("cover"):
        center.cover = request.FILES["cover"]
    center.save()

    return JsonResponse({
        "ok": True,
        "id": center.pk,
        "name_bn": center.name_bn,
        "name_en": center.name_en,
        "slug": center.slug,
        "message": f'"{center.name_bn}" সফলভাবে যোগ করা হয়েছে।',
    })


# ==================================================================
# EDIT (full page)
# ==================================================================
@staff_member_required
def center_edit(request, pk):
    """Edit an existing diagnostic center."""
    center = get_object_or_404(DiagnosticCenter, pk=pk)

    if request.method == "POST":
        data, errors = _extract_center_data(request)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "dashboard/diagnostic_center_form.html", {
                "center": center,
                "form_data": data,
                "mode": "edit",
                "page_title": f"সম্পাদনা: {center.name_bn}",
            })

        for field, value in data.items():
            setattr(center, field, value)
        if request.FILES.get("logo"):
            center.logo = request.FILES["logo"]
        if request.FILES.get("cover"):
            center.cover = request.FILES["cover"]
        center.save()

        messages.success(request, f'"{center.name_bn}" সফলভাবে আপডেট করা হয়েছে।')
        return redirect("dashboard:center_list")

    form_data = {
        "name_bn": center.name_bn,
        "name_en": center.name_en,
        "slug": center.slug,
        "area_bn": center.area_bn,
        "area_en": center.area_en,
        "address_bn": center.address_bn,
        "address_en": center.address_en,
        "phone": center.phone,
        "phone_alt": center.phone_alt,
        "email": center.email,
        "website": center.website,
        "latitude": center.latitude,
        "longitude": center.longitude,
        "map_url": center.map_url,
        "opening_hours_bn": center.opening_hours_bn,
        "opening_hours_en": center.opening_hours_en,
        "description_bn": center.description_bn,
        "description_en": center.description_en,
        "is_active": center.is_active,
        "is_verified": center.is_verified,
        "is_featured": center.is_featured,
    }

    return render(request, "dashboard/diagnostic_center_form.html", {
        "center": center,
        "form_data": form_data,
        "mode": "edit",
        "page_title": f"সম্পাদনা: {center.name_bn}",
    })


# ==================================================================
# DELETE (POST only)
# ==================================================================
@staff_member_required
@require_POST
def center_delete(request, pk):
    """Delete a diagnostic center."""
    center = get_object_or_404(DiagnosticCenter, pk=pk)
    name = center.name_bn
    center.delete()
    messages.success(request, f'"{name}" ডিলিট করা হয়েছে।')
    return redirect("dashboard:center_list")


# ==================================================================
# TOGGLE (AJAX) — verified / featured / active
# ==================================================================
@staff_member_required
@require_POST
def center_toggle(request, pk, field):
    """Toggle a boolean field via AJAX. Returns JSON."""
    if field not in ("is_active", "is_verified", "is_featured"):
        return JsonResponse({"ok": False, "error": "invalid_field"}, status=400)

    center = get_object_or_404(DiagnosticCenter, pk=pk)
    current = getattr(center, field)
    setattr(center, field, not current)

    update_fields = [field, "updated_at"]
    if field == "is_verified" and not current:
        center.last_verified_at = timezone.now()
        update_fields.append("last_verified_at")

    center.save(update_fields=update_fields)

    return JsonResponse({
        "ok": True,
        "field": field,
        "value": getattr(center, field),
    })


# ==================================================================
# HELPERS
# ==================================================================
def _extract_center_data(request):
    """
    Parse form POST data into a dict + collect validation errors.
    Returns (data_dict, errors_list).
    """
    post = request.POST
    errors = []

    name_bn = (post.get("name_bn") or "").strip()
    name_en = (post.get("name_en") or "").strip()

    if not name_bn:
        errors.append("বাংলা নাম আবশ্যক।")
    if not name_en:
        errors.append("English name is required.")

    def _float_or_none(key):
        val = (post.get(key) or "").strip()
        if not val:
            return None
        try:
            return float(val)
        except ValueError:
            errors.append(f"{key} must be a number.")
            return None

    data = {
        "name_bn": name_bn,
        "name_en": name_en,
        "slug": (post.get("slug") or "").strip(),
        "area_bn": (post.get("area_bn") or "").strip(),
        "area_en": (post.get("area_en") or "").strip(),
        "address_bn": (post.get("address_bn") or "").strip(),
        "address_en": (post.get("address_en") or "").strip(),
        "phone": (post.get("phone") or "").strip(),
        "phone_alt": (post.get("phone_alt") or "").strip(),
        "email": (post.get("email") or "").strip(),
        "website": (post.get("website") or "").strip(),
        "latitude": _float_or_none("latitude"),
        "longitude": _float_or_none("longitude"),
        "map_url": (post.get("map_url") or "").strip(),
        "opening_hours_bn": (post.get("opening_hours_bn") or "").strip(),
        "opening_hours_en": (post.get("opening_hours_en") or "").strip(),
        "description_bn": (post.get("description_bn") or "").strip(),
        "description_en": (post.get("description_en") or "").strip(),
        "is_active": post.get("is_active") == "on",
        "is_verified": post.get("is_verified") == "on",
        "is_featured": post.get("is_featured") == "on",
    }

    return data, errors