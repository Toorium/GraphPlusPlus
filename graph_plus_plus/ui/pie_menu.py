"""Pie menu — invoked via Ctrl+Shift+G (or whatever the user rebinds to)."""
import bpy
from bpy.types import Menu


class GPP_MT_pie_main(Menu):
    bl_label = "Graph++"
    bl_idname = "GPP_MT_pie_main"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # East (4) — Drag Keyframe
        pie.operator("gpp.path_drag", text="Drag Keyframe", icon='KEY_HLT')
        # West (6) — Drag Handle
        pie.operator("gpp.handle_drag", text="Drag Handle", icon='HANDLE_AUTOCLAMPED')
        # North (2) — Fix Arcs
        pie.operator("gpp.fix_arcs", text="Fix Arcs", icon='CURVE_BEZCURVE')
        # South (8) — Toggle Path
        pie.operator("gpp.toggle_path", text="Toggle Path", icon='OUTLINER_OB_CAMERA')
        # North-East (3) — Easing
        pie.operator("gpp.apply_easing", text="Easing...", icon='IPO_EASE_IN_OUT')
        # North-West (1) — Anticipation
        pie.operator("gpp.add_anticipation", text="Anticipation", icon='KEY_HLT')
        # South-East (9) — Follow-Through
        pie.operator("gpp.add_follow_through", text="Follow-Through", icon='KEY_HLT')
        # South-West (7) — Check Updates
        pie.operator("gpp.check_updates", text="Check Updates", icon='URL')


classes = (
    GPP_MT_pie_main,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[Graph++] unregister error for {cls.__name__}: {e}")
