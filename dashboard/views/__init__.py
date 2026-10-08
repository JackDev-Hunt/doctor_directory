"""
Dashboard views package.
"""

# ---- Dashboard home ----
from .dashboard import index  # noqa: F401

# ---- Diagnostic Center views ----
from .diagnostic_center_views import (  # noqa: F401
    center_list,
    center_create,
    center_create_ajax,
    center_edit,
    center_delete,
    center_toggle,
)

# ---- Doctor views ----
from .doctor_views import (  # noqa: F401
    doctor_list,
    doctor_create,
    doctor_edit,
    doctor_delete,
)

# ---- Specialist views ----
from .specialist_views import (  # noqa: F401
    specialist_list,
    specialist_create,
    specialist_edit,
    specialist_delete,
)

# Sub-modules
from . import dashboard                 # noqa: F401
from . import diagnostic_center_views   # noqa: F401
from . import doctor_views              # noqa: F401
from . import specialist_views          # noqa: F401


__all__ = [
    "index",
    "center_list", "center_create", "center_create_ajax",
    "center_edit", "center_delete", "center_toggle",
    "doctor_list", "doctor_create", "doctor_edit", "doctor_delete",
    "specialist_list", "specialist_create", "specialist_edit", "specialist_delete",
    "dashboard", "diagnostic_center_views", "doctor_views", "specialist_views",
]