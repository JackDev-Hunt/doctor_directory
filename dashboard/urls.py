from django.urls import path
from dashboard.views import dashboard as dash_views
from dashboard.views import diagnostic_center_views as center_views
from dashboard.views import doctor_views as doctor_v
from dashboard.views import specialist_views as spec_v

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

    # ---------- Doctors ----------
    # ---------- Doctors ----------
    path("doctors/",                       doctor_v.doctor_list,         name="doctor_list"),
    path("doctors/new/",                   doctor_v.doctor_create,       name="doctor_create"),
    path("doctors/new/ajax/",              doctor_v.doctor_create_ajax,  name="doctor_create_ajax"),   # ← NEW
    path("doctors/<int:pk>/edit/",         doctor_v.doctor_edit,         name="doctor_edit"),
    path("doctors/<int:pk>/delete/",       doctor_v.doctor_delete,       name="doctor_delete"),

    # ---------- Specialists ----------
    path("specialists/",                          spec_v.specialist_list,           name="specialist_list"),
    path("specialists/new/",                      spec_v.specialist_create,         name="specialist_create"),
    path("specialists/new/ajax/",                 spec_v.specialist_create_ajax,    name="specialist_create_ajax"),
    path("specialists/<int:pk>/edit/",            spec_v.specialist_edit,           name="specialist_edit"),
    path("specialists/<int:pk>/delete/",          spec_v.specialist_delete,         name="specialist_delete"),
]