"""N-panel UI — 'Graph++' tab in the View3D and Graph Editor sidebars."""
import bpy
from bpy.types import Panel


class GPP_PT_main(Panel):
    bl_label = "Graph++"
    bl_idname = "GPP_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Graph++"

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        # Header — version
        from .. import GPP_VERSION
        row = layout.row(align=True)
        row.label(text=f"Graph++ v{GPP_VERSION}", icon='INFO')
        row.operator("gpp.check_updates", text="", icon='URL')

        if obj is None:
            layout.label(text="No active object", icon='ERROR')
            return

        # Path toggle
        from ..motion_path.multi_object import is_enabled
        enabled = is_enabled(obj)
        row = layout.row(align=True)
        row.label(text="Motion Path:")
        op = row.operator("gpp.toggle_path", text="On" if not enabled else "Off", icon='OUTLINER_OB_CAMERA' if not enabled else 'CHECKMARK')
        # Pie / drag buttons
        col = layout.column(align=True)
        col.label(text="Edit on Path:", icon='CURVE_BEZCURVE')
        row = col.row(align=True)
        row.operator("gpp.path_drag", text="Drag Keyframe", icon='KEY_HLT')
        row.operator("gpp.handle_drag", text="Drag Handle", icon='HANDLE_AUTOCLAMPED')

        # Smart Tweaks
        box = layout.box()
        box.label(text="Smart Tweaks", icon='MODIFIER')
        box.operator("gpp.fix_arcs", text="Fix Arcs", icon='CURVE_BEZCURVE')
        box.operator("gpp.add_anticipation", text="Add Anticipation", icon='KEY_HLT')
        box.operator("gpp.add_follow_through", text="Add Follow-Through", icon='KEY_HLT')

        # Easing presets
        box = layout.box()
        box.label(text="Easing Presets", icon='IPO_EASE_IN_OUT')
        # The operator opens its own popup for preset selection
        box.operator("gpp.apply_easing", text="Apply Easing...", icon='IPO_EASE_IN_OUT')

        # Update section
        box = layout.box()
        box.label(text="Updates", icon='URL')
        prefs = context.preferences.addons.get("graph_plus_plus")
        if prefs and prefs.preferences:
            p = prefs.preferences
            if p.latest_version:
                box.label(text=f"Latest: v{p.latest_version}")
                if p.staged_zip_path:
                    box.label(text="Update staged. Restart to install.", icon='FILE_TICK')
                else:
                    box.operator("gpp.install_update", text="Download & Stage", icon='IMPORT')
            else:
                box.label(text="Not checked yet.")
                box.operator("gpp.check_updates", text="Check Now", icon='URL')


class GPP_PT_graph_editor(Panel):
    """Same panel in the Graph Editor sidebar for context convenience."""
    bl_label = "Graph++"
    bl_idname = "GPP_PT_graph_editor"
    bl_space_type = 'GRAPH_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Graph++"

    def draw(self, context):
        # Reuse the View3D panel's draw method
        GPP_PT_main.draw(self, context)


classes = (
    GPP_PT_main,
    GPP_PT_graph_editor,
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
