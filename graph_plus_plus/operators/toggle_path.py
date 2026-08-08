"""Toggle Graph++ path drawing for the active object."""
import bpy


class GPP_OT_toggle_path(bpy.types.Operator):
    """Toggle Graph++ motion path display for the active object"""
    bl_idname = "gpp.toggle_path"
    bl_label = "Toggle Graph++ Path"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        from ..motion_path.multi_object import is_enabled, set_enabled

        obj = context.active_object
        new_state = not is_enabled(obj)
        set_enabled(obj, new_state)

        # Tag the 3D view for redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        status = "enabled" if new_state else "disabled"
        self.report({'INFO'}, f"Graph++ path {status} for '{obj.name}'")
        return {'FINISHED'}
