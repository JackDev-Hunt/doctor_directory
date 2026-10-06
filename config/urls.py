"""Root URL configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Language switcher
    path('i18n/', include('django.conf.urls.i18n')),

    # Public website
    path('', include('website.urls')),

    # Custom dashboard (staff-only, Part 3 এ populate)
    path('dashboard/', include('dashboard.urls')),

    # REST API (Part 4 এ populate)
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Django admin branding
admin.site.site_header = "Netrakona Doctor Directory — Admin"
admin.site.site_title = "NKD Admin"
admin.site.index_title = "Manage Directory"