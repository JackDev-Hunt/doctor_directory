"""Root URL configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # Language switcher (i18n)
    path('i18n/', include('django.conf.urls.i18n')),

    # ---------- Authentication ----------
    # Login
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='auth/login.html'),
        name='login',
    ),
    # Logout (POST only for security)
    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(template_name='auth/logged_out.html'),
        name='logout',
    ),

    # ---------- Dashboard (custom) ----------
    path('dashboard/', include('dashboard.urls')),

    # ---------- Public website ----------
    path('', include('website.urls')),
]

# Serve media/static in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Django admin branding
admin.site.site_header = "Netrakona Doctor Directory — Admin"
admin.site.site_title = "NKD Admin"
admin.site.index_title = "Manage Directory"