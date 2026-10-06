from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

@staff_member_required
def index(request):
    """Custom dashboard landing page (staff-only). Part 3 এ full version।"""
    return render(request, 'dashboard/dashboard.html', {})