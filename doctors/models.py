"""
Core domain models for Netrakona Doctor Directory.
"""
from django.db import models
from django.utils.text import slugify


# ==================================================================
# ABSTRACT BASES
# ==================================================================
class TimeStampedModel(models.Model):
    """Abstract base with created_at / updated_at."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BilingualNameSlugModel(TimeStampedModel):
    """Abstract base with bn/en names and a unique slug."""
    name_bn = models.CharField("নাম (বাংলা)", max_length=200)
    name_en = models.CharField("Name (English)", max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name_en) or slugify(self.name_bn) or "item"
            slug = base
            i = 1
            while (
                self.__class__.objects
                .filter(slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name_bn or self.name_en


# ==================================================================
# WEEKDAY
# ==================================================================
class Weekday(models.TextChoices):
    SAT = "sat", "শনিবার / Saturday"
    SUN = "sun", "রবিবার / Sunday"
    MON = "mon", "সোমবার / Monday"
    TUE = "tue", "মঙ্গলবার / Tuesday"
    WED = "wed", "বুধবার / Wednesday"
    THU = "thu", "বৃহস্পতিবার / Thursday"
    FRI = "fri", "শুক্রবার / Friday"


# ==================================================================
# SPECIALIST
# ==================================================================
class Specialist(BilingualNameSlugModel):
    description_bn = models.TextField("বিবরণ (বাংলা)", blank=True)
    description_en = models.TextField("Description (English)", blank=True)
    icon = models.CharField("Icon (SVG name or emoji)", max_length=64, blank=True)
    is_featured = models.BooleanField("Featured?", default=False)
    is_active = models.BooleanField("Active?", default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Specialist"
        verbose_name_plural = "Specialists"
        ordering = ["display_order", "name_en"]
        indexes = [
            models.Index(fields=["is_active", "is_featured"]),
            models.Index(fields=["slug"]),
        ]

    def get_absolute_url(self):
        return f"/specialists/{self.slug}/"


# ==================================================================
# DIAGNOSTIC CENTER
# ==================================================================
class DiagnosticCenter(BilingualNameSlugModel):
    address_bn = models.CharField("ঠিকানা (বাংলা)", max_length=300, blank=True)
    address_en = models.CharField("Address (English)", max_length=300, blank=True)
    area_bn = models.CharField("এলাকা (বাংলা)", max_length=100, blank=True)
    area_en = models.CharField("Area (English)", max_length=100, blank=True)
    phone = models.CharField("ফোন", max_length=32, blank=True)
    phone_alt = models.CharField("বিকল্প ফোন", max_length=32, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    latitude = models.DecimalField(
        "Latitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        "Longitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    map_url = models.URLField("Google Maps URL", blank=True)

    logo = models.ImageField(upload_to="centers/", blank=True, null=True)
    cover = models.ImageField(upload_to="centers/covers/", blank=True, null=True)

    opening_hours_bn = models.CharField("খোলার সময় (বাংলা)", max_length=120, blank=True)
    opening_hours_en = models.CharField("Opening hours (English)", max_length=120, blank=True)
    description_bn = models.TextField("বিবরণ (বাংলা)", blank=True)
    description_en = models.TextField("Description (English)", blank=True)

    is_verified = models.BooleanField("Verified?", default=False)
    is_featured = models.BooleanField("Featured?", default=False)
    is_active = models.BooleanField("Active?", default=True)

    last_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Diagnostic Center"
        verbose_name_plural = "Diagnostic Centers"
        ordering = ["-is_featured", "name_en"]
        indexes = [
            models.Index(fields=["is_active", "is_verified"]),
            models.Index(fields=["area_en"]),
            models.Index(fields=["slug"]),
        ]

    def get_absolute_url(self):
        return f"/diagnostic-centers/{self.slug}/"

    @property
    def has_location(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def google_maps_link(self):
        if self.map_url:
            return self.map_url
        if self.has_location:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return ""


# ==================================================================
# DOCTOR
# ==================================================================
class Doctor(BilingualNameSlugModel):
    photo = models.ImageField(upload_to="doctors/", blank=True, null=True)
    qualification_bn = models.CharField("যোগ্যতা (বাংলা)", max_length=300, blank=True)
    qualification_en = models.CharField("Qualification (English)", max_length=300, blank=True)
    designation_bn = models.CharField("পদবি (বাংলা)", max_length=200, blank=True)
    designation_en = models.CharField("Designation (English)", max_length=200, blank=True)
    bio_bn = models.TextField("জীবনী (বাংলা)", blank=True)
    bio_en = models.TextField("Bio (English)", blank=True)
    experience_years = models.PositiveSmallIntegerField("অভিজ্ঞতা (বছর)", default=0)

    phone = models.CharField("ফোন", max_length=32, blank=True)
    phone_alt = models.CharField("বিকল্প ফোন", max_length=32, blank=True)
    email = models.EmailField(blank=True)
    bmdc_reg_no = models.CharField("BMDC Reg. No.", max_length=64, blank=True)

    specialists = models.ManyToManyField(
        Specialist, related_name="doctors", blank=True, verbose_name="Specialties"
    )

    is_verified = models.BooleanField("Verified?", default=False)
    is_featured = models.BooleanField("Featured?", default=False)
    is_active = models.BooleanField("Active?", default=True)

    last_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        ordering = ["-is_featured", "name_en"]
        indexes = [
            models.Index(fields=["is_active", "is_verified"]),
            models.Index(fields=["slug"]),
        ]

    def get_absolute_url(self):
        return f"/doctors/{self.slug}/"

    @property
    def primary_specialist(self):
        return self.specialists.first()


# ==================================================================
# CHAMBER (Schedule)
# ==================================================================
class Chamber(TimeStampedModel):
    """Doctor's visiting schedule at a diagnostic center."""

    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="chambers"
    )
    diagnostic_center = models.ForeignKey(
        DiagnosticCenter, on_delete=models.CASCADE, related_name="chambers"
    )
    day = models.CharField("দিন / Day", max_length=3, choices=Weekday.choices)
    start_time = models.TimeField("শুরু / Start")
    end_time = models.TimeField("শেষ / End")

    appointment_phone = models.CharField("অ্যাপয়েন্টমেন্ট ফোন", max_length=32, blank=True)
    room_no = models.CharField("রুম নম্বর", max_length=32, blank=True)
    notes_bn = models.CharField("নোট (বাংলা)", max_length=200, blank=True)
    notes_en = models.CharField("Notes (English)", max_length=200, blank=True)

    is_active = models.BooleanField("Active?", default=True)

    class Meta:
        verbose_name = "Chamber / Schedule"
        verbose_name_plural = "Chambers / Schedules"
        ordering = ["doctor__name_en", "day", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "diagnostic_center", "day", "start_time"],
                name="uniq_doctor_center_day_start",
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="chamber_end_after_start",
            ),
        ]
        indexes = [
            models.Index(fields=["day", "start_time"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.doctor} — {self.get_day_display()} @ {self.diagnostic_center}"

    @property
    def effective_phone(self):
        return (
            self.appointment_phone
            or self.diagnostic_center.phone
            or self.doctor.phone
        )


    