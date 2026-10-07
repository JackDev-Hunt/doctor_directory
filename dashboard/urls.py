from django.urls import path
from dashboard.views import dashboard as dash_views
from dashboard.views import diagnostic_center_views as center_views

app_name = "dashboard"

urlpatterns = [
    # Dashboard home
    path("", dash_views.index, name="index"),

    # ---------- Diagnostic Centers ----------
    path("centers/",                              center_views.center_list,        name="center_list"),
    path("centers/new/",                          center_views.center_create,      name="center_create"),
    path("centers/new/ajax/",                     center_views.center_create_ajax, name="center_create_ajax"),
    path("centers/<int:pk>/edit/",                center_views.center_edit,        name="center_edit"),
    path("centers/<int:pk>/delete/",              center_views.center_delete,      name="center_delete"),
    path("centers/<int:pk>/toggle/<str:field>/",  center_views.center_toggle,      name="center_toggle"),
]