"""Fix Arcs operator — detect instant rotations and replace with bezier arcs.

Wraps core.arc_generator.find_instant_rotations() and apply_arc_to_segment()
into a single user-facing operator with an 'arc_amount' slider.
"""
import bpy


class GPP_OT_fix_arcs(bpy.types.Operator):
    """Detect instant/linear rotations on the active object and replace them with smooth bezier arcs"""
    bl_idname = "gpp.fix_arcs"
    bl_label = "Fix Arcs"
    bl_description = "Find instant/linear rotation keyframes and convert them to smooth bezier arcs"
    bl_options = {'REGISTER', 'UNDO'}

    arc_amount: bpy.props.FloatProperty(
        name="Arc Amount",
        description="0 = no change, 1 = full perpendicular arc, >1 = exaggerated",
        default=1.0,
        min=0.0,
        max=3.0,
    )

    threshold: bpy.props.FloatProperty(
        name="Detection Threshold",
        description="Lower = stricter (only obvious instant rotations), Higher = more aggressive",
        default=0.001,
        min=0.0001,
        max=0.1,
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        from ..core.arc_generator import find_instant_rotations, apply_arc_to_segment

        obj = context.active_object
        candidates = find_instant_rotations(obj, threshold=self.threshold)

        if not candidates:
            self.report({'INFO'}, "No instant rotations found on active object.")
            return {'CANCELLED'}

        applied = 0
        for seg in candidates:
            if apply_arc_to_segment(obj, seg, arc_amount=self.arc_amount):
                applied += 1

        # Invalidate path cache so the redraw reflects the new arcs
        from ..core.path_sampler import invalidate_cache
        invalidate_cache(obj)

        # Force redraw
        for area in context.screen.areas:
            if area.type in ('VIEW_3D', 'GRAPH_EDITOR', 'DOPESHEET_EDITOR'):
                area.tag_redraw()

        self.report({'INFO'}, f"Applied arc to {applied} rotation segment(s).")
        return {'FINISHED'}
