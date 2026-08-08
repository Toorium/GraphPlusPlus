"""Add Follow-Through operator — auto-insert settle/overshoot keys AFTER
each selected keyframe based on the action's velocity.

Two modes:
  - Settle: small keys that decay toward the target value (like a damped spring)
  - Overshoot: a single key past the target, then return
"""
import bpy
import math
from mathutils import Vector

from ..core.fcurve_access import (
    find_fcurve, get_loc_fcurves, commit_fcurve, get_action,
)
from ..core.path_sampler import sample_object_path


class GPP_OT_add_follow_through(bpy.types.Operator):
    """Add follow-through (settle/overshoot) keys after each selected keyframe"""
    bl_idname = "gpp.add_follow_through"
    bl_label = "Add Follow-Through"
    bl_description = "Auto-insert overshoot/settle keys after each selected keyframe, in the direction of motion"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(
        name="Mode",
        description="Type of follow-through to add",
        items=[
            ('OVERSHOOT', "Overshoot", "Single key past the target, then return"),
            ('SETTLE', "Settle", "Multiple decaying keys, like a damped spring"),
            ('BOTH', "Overshoot + Settle", "Overshoot key followed by decaying settle keys"),
        ],
        default='BOTH',
    )

    overshoot_frames: bpy.props.IntProperty(
        name="Overshoot Frames",
        description="Frames after the selected keyframe for the overshoot peak",
        default=6,
        min=1,
        max=60,
    )

    settle_frames: bpy.props.IntProperty(
        name="Settle Frames",
        description="Total settle duration after the overshoot",
        default=18,
        min=4,
        max=120,
    )

    overshoot_strength: bpy.props.FloatProperty(
        name="Overshoot Strength",
        description="How far past the target to overshoot (in Blender units)",
        default=0.3,
        min=0.0,
        max=10.0,
    )

    settle_bounces: bpy.props.IntProperty(
        name="Settle Bounces",
        description="Number of decaying bounces during settle (SETTLE mode)",
        default=3,
        min=1,
        max=10,
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

        loc_fcurves = get_loc_fcurves(obj)

        # Find selected location keyframes (use axis 0 as lead)
        lead_axis = None
        selected_kps = []
        for ax in range(3):
            fc = loc_fcurves[ax]
            if fc and not fc.lock:
                for kp in fc.keyframe_points:
                    if kp.select_control_point:
                        selected_kps.append(kp)
                if selected_kps and lead_axis is None:
                    lead_axis = ax
                    break

        if lead_axis is None or not selected_kps:
            self.report({'WARNING'}, "No location keyframes selected.")
            return {'CANCELLED'}

        # Sample the path for velocity direction at each selected keyframe
        path = sample_object_path(obj, samples_per_segment=4)
        path_dict = {round(p['frame']): p for p in path}

        added = 0
        for kp in selected_kps:
            target_frame = int(round(kp.co.x))

            # Find direction of motion at the target
            path_entry = path_dict.get(target_frame)
            if path_entry is None:
                continue

            next_path = None
            for p in path:
                if p['frame'] > target_frame:
                    next_path = p
                    break

            if next_path is None:
                # Use previous direction instead
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

            try:
                local_dir = obj.matrix_world.inverted().to_3x3() @ direction
            except Exception:
                local_dir = direction

            # Compute keyframe sequence based on mode
            keys_to_add = []  # list of (frame, offset_strength_multiplier)

            if self.mode in ('OVERSHOOT', 'BOTH'):
                # Single overshoot key
                keys_to_add.append((target_frame + self.overshoot_frames, self.overshoot_strength))
                if self.mode == 'BOTH':
                    # Add settle bounces after overshoot
                    settle_start = target_frame + self.overshoot_frames
                    settle_per_bounce = max(2, (self.settle_frames - self.overshoot_frames) // self.settle_bounces)
                    for b in range(self.settle_bounces):
                        # Decaying amplitude, alternating direction
                        amp = -self.overshoot_strength * (0.6 ** (b + 1))
                        f = settle_start + settle_per_bounce * (b + 1)
                        keys_to_add.append((f, amp))

            elif self.mode == 'SETTLE':
                # Pure decaying bounces from target
                settle_per_bounce = max(2, self.settle_frames // self.settle_bounces)
                for b in range(self.settle_bounces):
                    amp = self.overshoot_strength * (0.5 ** (b + 1)) * ((-1) ** b)
                    f = target_frame + settle_per_bounce * (b + 1)
                    keys_to_add.append((f, amp))

            # Insert the keyframes
            for ax in range(3):
                fc = loc_fcurves[ax]
                if fc is None:
                    continue
                for f, amp in keys_to_add:
                    current_val = fc.evaluate(f)
                    new_val = current_val + local_dir[ax] * amp
                    fc.keyframe_points.insert(f, new_val, options={'FAST'})
                    # Set handle types for smooth settle
                    for k in fc.keyframe_points:
                        if abs(k.co.x - f) < 0.5:
                            k.handle_left_type = "AUTO_CLAMPED"
                            k.handle_right_type = "AUTO_CLAMPED"
                            break
                    commit_fcurve(fc)

            added += 1

        for area in context.screen.areas:
            if area.type in ('VIEW_3D', 'GRAPH_EDITOR', 'DOPESHEET_EDITOR'):
                area.tag_redraw()

        self.report({'INFO'}, f"Added follow-through to {added} keyframe(s).")
        return {'FINISHED'}
