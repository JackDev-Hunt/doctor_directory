"""
Custom staff dashboard — simple starter version.
Will grow as we add features.
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def index(request):
    """
    Simple dashboard home page.
    Only accessible to logged-in staff users.
    """
    return render(request, "dashboard/dashboard.html", {
        "page_title": "ড্যাশবোর্ড",
    })