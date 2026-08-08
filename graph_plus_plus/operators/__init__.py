"""Graph++ operators package.

Each operator lives in its own module for clarity. This __init__ registers
them all in a single batch.
"""
import bpy
from bpy.props import (
    EnumProperty, FloatProperty, IntProperty, BoolProperty, StringProperty,
    FloatVectorProperty,
)


def _gather_operators():
    """Import and return list of operator classes from each submodule."""
    from .path_drag import GPP_OT_path_drag
    from .handle_drag import GPP_OT_handle_drag
    from .apply_easing import GPP_OT_apply_easing
    from .add_anticipation import GPP_OT_add_anticipation
    from .add_follow_through import GPP_OT_add_follow_through
    from .fix_arcs import GPP_OT_fix_arcs
    from .toggle_path import GPP_OT_toggle_path
    from .check_updates import GPP_OT_check_updates
    from .install_update import GPP_OT_install_update

    return [
        GPP_OT_path_drag,
        GPP_OT_handle_drag,
        GPP_OT_apply_easing,
        GPP_OT_add_anticipation,
        GPP_OT_add_follow_through,
        GPP_OT_fix_arcs,
        GPP_OT_toggle_path,
        GPP_OT_check_updates,
        GPP_OT_install_update,
    ]


classes = _gather_operators()


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[Graph++] unregister error for {cls.__name__}: {e}")
