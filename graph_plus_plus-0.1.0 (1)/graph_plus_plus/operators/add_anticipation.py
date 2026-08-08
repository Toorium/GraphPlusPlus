"""Add Anticipation operator — auto-insert a lead-in keyframe before each
selected keyframe based on the action's velocity.

The new keyframe is placed ~5-10 frames before the selected one, with a
position offset opposite to the direction of motion. This produces the
classic anticipation pull-back that gives animation weight.
"""
import bpy
import math
from mathutils import Vector

from ..core.fcurve_access import (
    find_fcurve, get_loc_fcurves, commit_fcurve, get_action,
)
from ..core.path_sampler import sample_object_path


class GPP_OT_add_anticipation(bpy.types.Operator):
    """Add an anticipation keyframe before each selected keyframe"""
    bl_idname = "gpp.add_anticipation"
    bl_label = "Add Anticipation"
    bl_description = "Auto-insert a lead-in keyframe before each selected keyframe, opposite to motion direction"
    bl_options = {'REGISTER', 'UNDO'}

    lead_frames: bpy.props.IntProperty(
        name="Lead Frames",
        description="Number of frames before the selected keyframe to place the anticipation key",
        default=8,
        min=1,
        max=60,
    )

    offset_strength: bpy.props.FloatProperty(
        name="Offset Strength",
        description="How far to offset the anticipation key from the selected keyframe (in Blender units)",
        default=0.5,
        min=0.0,
        max=10.0,
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        action = get_action(obj)
        if action is None:
            self.report({'WARNING'}, "Active object has no animation action.")
            return {'CANCELLED'}

        # Find selected location keyframes
        loc_fcurves = get_loc_fcurves(obj)
        selected_kps_per_axis = []
        for ax, fc in enumerate(loc_fcurves):
            selected = []
            if fc and not fc.lock:
                for kp in fc.keyframe_points:
                    if kp.select_control_point:
                        selected.append(kp)
            selected_kps_per_axis.append(selected)

        # Use axis 0 (location X) as the lead — if no keyframes there, try 1, then 2
        lead_axis = None
        for ax in range(3):
            if selected_kps_per_axis[ax]:
                lead_axis = ax
                break

        if lead_axis is None:
            self.report({'WARNING'}, "No location keyframes selected.")
            return {'CANCELLED'}

        # Sample the path to compute velocity direction at each selected keyframe
        path = sample_object_path(obj, samples_per_segment=4)
        path_dict = {round(p['frame']): p for p in path}

        added = 0
        for kp in selected_kps_per_axis[lead_axis]:
            target_frame = int(round(kp.co.x))
            anticipation_frame = target_frame - self.lead_frames

            # Find the velocity direction at this keyframe
            # (use the segment AFTER the keyframe — the action direction)
            path_entry = path_dict.get(target_frame)
            if path_entry is None:
                continue

            # Find the next path sample for direction
            next_path = None
            for p in path:
                if p['frame'] > target_frame:
                    next_path = p
                    break

            if next_path is None:
                # No forward motion — use backward direction instead
                prev_path = None
                for p in reversed(path):
                    if p['frame'] < target_frame:
                        prev_path = p
                        break
                if prev_path is None:
                    continue
                direction = (path_entry['point'] - prev_path['point']).normalized()
            else:
                direction = (next_path['point'] - path_entry['point']).normalized()

            # Anticipation = opposite direction, scaled by offset_strength
            offset_world = -direction * self.offset_strength
            # Convert offset from world to local (use object's current world matrix)
            try:
                local_offset = obj.matrix_world.inverted().to_3x3() @ offset_world
            except Exception:
                local_offset = offset_world

            # Insert keyframes on all 3 location channels at anticipation_frame
            # with values = (current location at that frame) + offset
            for ax in range(3):
                fc = loc_fcurves[ax]
                if fc is None:
                    continue
                # Sample the FCurve at anticipation_frame to get the current value
                current_val = fc.evaluate(anticipation_frame)
                new_val = current_val + local_offset[ax]
                # Insert keyframe
                fc.keyframe_points.insert(anticipation_frame, new_val, options={'FAST'})
                # Set the new keyframe's right handle to AUTO_CLAMPED for smooth
                # transition into the target keyframe.
                new_kp = None
                for k in fc.keyframe_points:
                    if abs(k.co.x - anticipation_frame) < 0.5:
                        new_kp = k
                        break
                if new_kp:
                    new_kp.handle_right_type = "AUTO_CLAMPED"
                    new_kp.handle_left_type = "VECTOR"  # sharp exit from anticipation
                commit_fcurve(fc)

            added += 1

        # Invalidate path cache so the redraw reflects the new anticipation keys
        from ..core.path_sampler import invalidate_cache
        invalidate_cache(obj)

        for area in context.screen.areas:
            if area.type in ('VIEW_3D', 'GRAPH_EDITOR', 'DOPESHEET_EDITOR'):
                area.tag_redraw()

        self.report({'INFO'}, f"Added anticipation to {added} keyframe(s).")
        return {'FINISHED'}
