from django.urls import path
from dashboard.views import dashboard as dash_views

app_name = 'dashboard'

urlpatterns = [
    path('', dash_views.index, name='index'),
    # Part 3 এ আরও যোগ হবে
]