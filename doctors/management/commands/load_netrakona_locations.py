"""
Management command to load Netrakona district and its upazilas.

Usage:
    python manage.py load_netrakona_locations
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from doctors.models import District, Upazila


NETRAKONA_UPAZILAS = [
    ("নেত্রকোনা সদর", "Netrakona Sadar", 1),
    ("আটপাড়া", "Atpara", 2),
    ("বারহাট্টা", "Barhatta", 3),
    ("দুর্গাপুর", "Durgapur", 4),
    ("কলমাকান্দা", "Kalmakanda", 5),
    ("খালিয়াজুরী", "Khaliajuri", 6),
    ("মদন", "Madan", 7),
    ("মোহনগঞ্জ", "Mohanganj", 8),
    ("পূর্বধলা", "Purbadhala", 9),
    ("কেন্দুয়া", "Kendua", 10),
]


class Command(BaseCommand):
    help = "Load Netrakona district and upazilas"

    def handle(self, *args, **options):
        # Create/get Netrakona district
        district, created = District.objects.get_or_create(
            name_en="Netrakona",
            defaults={
                "name_bn": "নেত্রকোনা",
                "division_bn": "ময়মনসিংহ",
                "division_en": "Mymensingh",
                "slug": "netrakona",
                "is_active": True,
                "display_order": 1,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Created district: {district.name_bn}"))
        else:
            self.stdout.write(self.style.WARNING(f"✓ District already exists: {district.name_bn}"))

        # Create upazilas
        added = 0
        skipped = 0
        for name_bn, name_en, order in NETRAKONA_UPAZILAS:
            upazila, created = Upazila.objects.get_or_create(
                district=district,
                name_en=name_en,
                defaults={
                    "name_bn": name_bn,
                    "display_order": order,
                    "is_active": True,
                    "slug": f"{slugify(name_en)}-netrakona",
                },
            )
            if created:
                added += 1
                self.stdout.write(self.style.SUCCESS(f"  + {name_bn} ({name_en})"))
            else:
                skipped += 1
                self.stdout.write(f"  · {name_bn} already exists")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Done! Added: {added}, Skipped: {skipped}"))