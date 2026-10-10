"""
Custom dashboard views for Specialist management.
"""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from doctors.models import Specialist


# ==================================================================
# LIST
# ==================================================================
@staff_member_required
def specialist_list(request):
    """Display all specialists with search / filter / pagination."""
    qs = Specialist.objects.annotate(doctor_count=Count("doctors", distinct=True))

    # Search
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(name_bn__icontains=q) | Q(name_en__icontains=q) | Q(description_en__icontains=q)
        )

    # Filter
    status = request.GET.get("status", "").strip()
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)
    elif status == "featured":
        qs = qs.filter(is_featured=True)

    # Sort
    sort = request.GET.get("sort", "display_order").strip()
    allowed_sorts = {
        "name": "name_en",
        "-name": "-name_en",
        "order": "display_order",
        "-order": "-display_order",
        "newest": "-created_at",
        "oldest": "created_at",
    }
    qs = qs.order_by(allowed_sorts.get(sort, "display_order"), "name_en")

    # Pagination
    paginator = Paginator(qs, 16)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    # KPI
    total = Specialist.objects.count()
    active_count = Specialist.objects.filter(is_active=True).count()
    featured_count = Specialist.objects.filter(is_featured=True).count()
    with_doctors = Specialist.objects.annotate(dc=Count("doctors")).filter(dc__gt=0).count()

    context = {
        "page_obj": page_obj,
        "q": q,
        "status": status,
        "sort": sort,
        "total": total,
        "active_count": active_count,
        "featured_count": featured_count,
        "with_doctors": with_doctors,
        "page_title": "Specialists",
    }
    return render(request, "dashboard/specialist_list.html", context)


# ==================================================================
# CREATE (AJAX from modal)
# ==================================================================
@staff_member_required
@require_POST
def specialist_create_ajax(request):
    """
    Create a new specialist via AJAX (from modal on list page).
    Returns JSON: {ok: true, id, name_en, redirect: url} or {ok: false, errors: [...]}
    """
    data, errors = _extract_specialist_data(request)

    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)

    specialist = Specialist(**data)
    specialist.save()

    return JsonResponse({
        "ok": True,
        "id": specialist.pk,
        "name_bn": specialist.name_bn,
        "name_en": specialist.name_en,
        "slug": specialist.slug,
        "message": '"' + specialist.name_bn + '" added successfully.',
    })


# ==================================================================
# CREATE (full page — kept as fallback)
# ==================================================================
@staff_member_required
def specialist_create(request):
    return _specialist_form(request, specialist=None)


# ==================================================================
# EDIT
# ==================================================================
@staff_member_required
def specialist_edit(request, pk):
    specialist = get_object_or_404(Specialist, pk=pk)
    return _specialist_form(request, specialist=specialist)


def _specialist_form(request, specialist):
    """Shared create/edit logic."""
    is_edit = specialist is not None

    if request.method == "POST":
        data, errors = _extract_specialist_data(request)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, "dashboard/specialist_form.html", {
                "form_data": data,
                "mode": "edit" if is_edit else "create",
                "specialist": specialist,
                "page_title": ("Edit: " + specialist.name_en) if is_edit else "New Specialist",
            })

        if is_edit:
            for field, value in data.items():
                setattr(specialist, field, value)
            specialist.save()
            messages.success(request, '"' + specialist.name_bn + '" updated successfully.')
        else:
            specialist = Specialist(**data)
            specialist.save()
            messages.success(request, '"' + specialist.name_bn + '" added successfully.')

        return redirect("dashboard:specialist_list")

    # GET
    if is_edit:
        form_data = {
            "name_bn": specialist.name_bn,
            "name_en": specialist.name_en,
            "slug": specialist.slug,
            "description_bn": specialist.description_bn,
            "description_en": specialist.description_en,
            "icon": specialist.icon,
            "display_order": specialist.display_order,
            "is_active": specialist.is_active,
            "is_featured": specialist.is_featured,
        }
    else:
        form_data = {"is_active": True, "display_order": 0}

    return render(request, "dashboard/specialist_form.html", {
        "form_data": form_data,
        "mode": "edit" if is_edit else "create",
        "specialist": specialist,
        "page_title": ("Edit: " + specialist.name_en) if is_edit else "New Specialist",
    })


# ==================================================================
# DELETE
# ==================================================================
@staff_member_required
@require_POST
def specialist_delete(request, pk):
    specialist = get_object_or_404(Specialist, pk=pk)
    name = specialist.name_bn
    doctor_count = specialist.doctors.count()

    if doctor_count > 0:
        messages.error(request, 'Cannot delete "' + name + '" — ' + str(doctor_count) + ' doctor(s) are using it.')
        return redirect("dashboard:specialist_list")

    specialist.delete()
    messages.success(request, '"' + name + '" deleted.')
    return redirect("dashboard:specialist_list")


# ==================================================================
# HELPERS
# ==================================================================
def _extract_specialist_data(request):
    post = request.POST
    errors = []

    name_bn = (post.get("name_bn") or "").strip()
    name_en = (post.get("name_en") or "").strip()

    if not name_bn:
        errors.append("Bangla name is required.")
    if not name_en:
        errors.append("English name is required.")

    order_raw = (post.get("display_order") or "").strip()
    try:
        display_order = int(order_raw) if order_raw else 0
        if display_order < 0:
            display_order = 0
    except ValueError:
        errors.append("Display order must be a number.")
        display_order = 0

    data = {
        "name_bn": name_bn,
        "name_en": name_en,
        "slug": (post.get("slug") or "").strip(),
        "description_bn": (post.get("description_bn") or "").strip(),
        "description_en": (post.get("description_en") or "").strip(),
        "icon": (post.get("icon") or "").strip(),
        "display_order": display_order,
        "is_active": post.get("is_active") == "on",
        "is_featured": post.get("is_featured") == "on",
    }
    return data, errors