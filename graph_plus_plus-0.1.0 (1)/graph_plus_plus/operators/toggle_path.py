"""Toggle Graph++ path drawing for the active object, plus a manual refresh operator."""
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
        from ..motion_path.multi_object import is_enabled, set_enabled, invalidate_enabled_cache
        from ..core.path_sampler import invalidate_cache

        obj = context.active_object
        new_state = not is_enabled(obj)
        set_enabled(obj, new_state)
        invalidate_enabled_cache()
        invalidate_cache(obj)

        # Tag the 3D view for redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        status = "enabled" if new_state else "disabled"
        self.report({'INFO'}, f"Graph++ path {status} for '{obj.name}'")
        return {'FINISHED'}


class GPP_OT_refresh_path(bpy.types.Operator):
    """Force-refresh the Graph++ motion path cache for the active object"""
    bl_idname = "gpp.refresh_path"
    bl_label = "Refresh Path"
    bl_description = "Force a full re-sample of the motion path (use if the path looks stale)"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        from ..core.path_sampler import invalidate_cache
        from ..motion_path.multi_object import invalidate_enabled_cache

        obj = context.active_object
        invalidate_cache(obj)
        invalidate_enabled_cache()

        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        self.report({'INFO'}, f"Path cache cleared for '{obj.name}'.")
        return {'FINISHED'}
