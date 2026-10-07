"""Admin configuration for doctor-domain models."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import Specialist, DiagnosticCenter, Doctor, Chamber


# ==================================================================
# SPECIALIST
# ==================================================================
@admin.register(Specialist)
class SpecialistAdmin(admin.ModelAdmin):
    list_display = ("name_bn", "name_en", "slug", "is_featured", "is_active", "display_order")
    list_filter = ("is_active", "is_featured")
    search_fields = ("name_bn", "name_en", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
    list_editable = ("is_featured", "is_active", "display_order")
    ordering = ("display_order", "name_en")


# ==================================================================
# CHAMBER (inline inside Doctor)
# ==================================================================
class ChamberInline(admin.TabularInline):
    model = Chamber
    extra = 1
    fields = (
        "diagnostic_center", "day", "start_time", "end_time",
        "room_no", "appointment_phone", "is_active",
    )
    autocomplete_fields = ("diagnostic_center",)


# ==================================================================
# DOCTOR
# ==================================================================
@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = (
        "photo_tag", "name_bn", "name_en", "specialties_list",
        "phone", "is_verified", "is_featured", "is_active",
    )
    list_filter = ("is_active", "is_verified", "is_featured", "specialists")
    search_fields = ("name_bn", "name_en", "phone", "bmdc_reg_no", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
    filter_horizontal = ("specialists",)
    inlines = [ChamberInline]
    list_editable = ("is_verified", "is_featured", "is_active")
    readonly_fields = ("created_at", "updated_at", "last_verified_at")
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        ("Basic Information", {
            "fields": ("name_bn", "name_en", "slug", "photo")
        }),
        ("Professional Details", {
            "fields": (
                "specialists",
                "qualification_bn", "qualification_en",
                "designation_bn", "designation_en",
                "experience_years", "bmdc_reg_no",
            )
        }),
        ("Biography", {
            "fields": ("bio_bn", "bio_en"),
            "classes": ("collapse",),
        }),
        ("Contact", {
            "fields": ("phone", "phone_alt", "email"),
        }),
        ("Status", {
            "fields": (
                "is_verified", "is_featured", "is_active",
                "last_verified_at", "created_at", "updated_at",
            )
        }),
    )

    @admin.display(description="ছবি")
    def photo_tag(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:42px;height:42px;border-radius:50%;object-fit:cover;" />',
                obj.photo.url,
            )
        return "—"

    @admin.display(description="Specialties")
    def specialties_list(self, obj):
        names = [s.name_bn for s in obj.specialists.all()[:3]]
        return ", ".join(names) if names else "—"

    actions = ["mark_verified", "unmark_verified"]

    @admin.action(description="Mark selected as Verified")
    def mark_verified(self, request, queryset):
        updated = queryset.update(is_verified=True, last_verified_at=timezone.now())
        self.message_user(request, f"{updated} doctor(s) marked verified.")

    @admin.action(description="Mark selected as Unverified")
    def unmark_verified(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f"{updated} doctor(s) marked unverified.")


# ==================================================================
# DIAGNOSTIC CENTER  ← এটাই miss ছিল
# ==================================================================
@admin.register(DiagnosticCenter)
class DiagnosticCenterAdmin(admin.ModelAdmin):
    list_display = (
        "name_bn", "name_en", "area_en", "phone",
        "is_verified", "is_featured", "is_active",
    )
    list_filter = ("is_active", "is_verified", "is_featured", "area_en")
    search_fields = ("name_bn", "name_en", "phone", "area_bn", "area_en", "slug")
    prepopulated_fields = {"slug": ("name_en",)}
    list_editable = ("is_verified", "is_featured", "is_active")
    readonly_fields = ("created_at", "updated_at", "last_verified_at")

    fieldsets = (
        ("Basic", {
            "fields": ("name_bn", "name_en", "slug", "logo", "cover")
        }),
        ("Address", {
            "fields": ("address_bn", "address_en", "area_bn", "area_en")
        }),
        ("Contact", {
            "fields": ("phone", "phone_alt", "email", "website")
        }),
        ("Location", {
            "fields": ("latitude", "longitude", "map_url"),
        }),
        ("Details", {
            "fields": (
                "opening_hours_bn", "opening_hours_en",
                "description_bn", "description_en",
            ),
            "classes": ("collapse",),
        }),
        ("Status", {
            "fields": (
                "is_verified", "is_featured", "is_active",
                "last_verified_at", "created_at", "updated_at",
            )
        }),
    )


# ==================================================================
# CHAMBER (standalone admin view)
# ==================================================================
@admin.register(Chamber)
class ChamberAdmin(admin.ModelAdmin):
    list_display = (
        "doctor", "diagnostic_center", "day", "start_time", "end_time",
        "room_no", "is_active",
    )
    list_filter = ("day", "is_active", "diagnostic_center")
    search_fields = (
        "doctor__name_bn", "doctor__name_en",
        "diagnostic_center__name_bn", "diagnostic_center__name_en",
    )
    autocomplete_fields = ("doctor", "diagnostic_center")
    list_editable = ("is_active",)
    list_per_page = 30