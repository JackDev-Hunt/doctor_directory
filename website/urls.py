from django.urls import path
from website.views import home_views

app_name = 'website'

urlpatterns = [
    path('', home_views.home, name='home'),
    # Part 7+ এ যোগ হবে: doctor list, profile, specialist, center
]