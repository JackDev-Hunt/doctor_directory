"""
Dashboard views package.

সব public views এখানে import করা হয় যাতে:
  from dashboard.views import dashboard
  from dashboard.views import diagnostic_center_views
— এভাবে ব্যবহার করা যায়।
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

# Sub-modules (for `views.dashboard.index` style access)
from . import dashboard                 # noqa: F401
from . import diagnostic_center_views   # noqa: F401


__all__ = [
    # Home
    "index",

    # Diagnostic center
    "center_list",
    "center_create",
    "center_create_ajax",
    "center_edit",
    "center_delete",
    "center_toggle",

    # Modules
    "dashboard",
    "diagnostic_center_views",
]