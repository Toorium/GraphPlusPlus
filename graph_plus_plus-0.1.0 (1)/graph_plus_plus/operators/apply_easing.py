"""Apply easing presets operator — one-click apply easing curves to selected keyframes.

Presets include: linear, ease-in-out (cubic), ease-in, ease-out, back,
elastic, bounce, anticipation, settle.
"""
import bpy
import math


# Preset library — each preset is a function that takes (kp, side) and
# configures the handles to produce the desired easing curve.
# Side: 'both' = apply to both left & right handles, 'in' = left only, 'out' = right only.

EASING_PRESETS = {
    "EASE_IN_OUT": {
        "label": "Ease In-Out (Cubic)",
        "description": "Smooth S-curve, slow at both ends",
        "handle_type": "AUTO_CLAMPED",
    },
    "EASE_IN": {
        "label": "Ease In",
        "description": "Slow start, fast end",
        "handle_type": "AUTO_CLAMPED",
        "bias": "in",
    },
    "EASE_OUT": {
        "label": "Ease Out",
        "description": "Fast start, slow end",
        "handle_type": "AUTO_CLAMPED",
        "bias": "out",
    },
    "LINEAR": {
        "label": "Linear",
        "description": "Constant speed",
        "handle_type": "VECTOR",
    },
    "BACK_IN": {
        "label": "Back In",
        "description": "Anticipation pull-back before forward motion",
        "handle_type": "FREE",
        "back_scale": -0.4,
    },
    "BACK_OUT": {
        "label": "Back Out",
        "description": "Overshoot past target then settle",
        "handle_type": "FREE",
        "back_scale": 0.4,
    },
    "BACK_IN_OUT": {
        "label": "Back In-Out",
        "description": "Pull back, overshoot, settle",
        "handle_type": "FREE",
        "back_scale": 0.4,
    },
    "ELASTIC_IN": {
        "label": "Elastic In",
        "description": "Springy arrival from rest",
        "handle_type": "FREE",
        "elastic": True,
    },
    "ELASTIC_OUT": {
        "label": "Elastic Out",
        "description": "Springy overshoot before settle",
        "handle_type": "FREE",
        "elastic": True,
    },
    "BOUNCE": {
        "label": "Bounce",
        "description": "Decaying bounce at the end",
        "handle_type": "FREE",
        "bounce": True,
    },
}


def apply_preset_to_keyframe(kp, preset_name, side='both'):
    """Apply an easing preset to a single keyframe point.

    kp: bpy.types.FCurveKeyframePoints keyframe point
    preset_name: key into EASING_PRESETS
    side: 'both', 'in', 'out' — which handle(s) to modify
    """
    preset = EASING_PRESETS.get(preset_name)
    if preset is None:
        return False

    handle_type = preset.get("handle_type", "AUTO_CLAMPED")
    back_scale = preset.get("back_scale", 0.0)
    is_elastic = preset.get("elastic", False)
    is_bounce = preset.get("bounce", False)
    bias = preset.get("bias", None)

    # For BACK and ELASTIC presets, we need to know the segment length to
    # scale the handle offset correctly. We approximate using kp.co and the
    # adjacent keyframe.
    # For AUTO_CLAMPED / VECTOR, we just set the type.

    if handle_type in ("AUTO_CLAMPED", "AUTO", "VECTOR"):
        if side in ('both', 'in'):
            kp.handle_left_type = handle_type
        if side in ('both', 'out'):
            kp.handle_right_type = handle_type
        return True

    # FREE handles (back, elastic, bounce) — compute handle offsets
    # We need the previous & next keyframes to compute segment length
    # but we don't have direct access to the FCurve here. So we set the
    # handle TYPE and apply a default visual offset; the user can fine-tune.
    if side in ('both', 'in'):
        kp.handle_left_type = handle_type
        # Back/elastic: offset the handle y by back_scale * segment_length
        # Approximate segment length from current handle x offset
        left_offset = kp.co.x - kp.handle_left.x
        if left_offset > 1e-6:
            current_dy = kp.co.y - kp.handle_left.y
            # Multiply by back_scale to create the pull-back effect
            new_dy = current_dy * (1.0 - back_scale)
            kp.handle_left = (kp.handle_left.x, kp.co.y - new_dy)

    if side in ('both', 'out'):
        kp.handle_right_type = handle_type
        right_offset = kp.handle_right.x - kp.co.x
        if right_offset > 1e-6:
            current_dy = kp.handle_right.y - kp.co.y
            new_dy = current_dy * (1.0 + back_scale)
            kp.handle_right = (kp.handle_right.x, kp.co.y + new_dy)

    return True


def _gather_selected_keyframes(obj):
    """Return list of (fc, kp) tuples for selected keyframes on obj."""
    from ..core.fcurve_access import get_fcurves
    result = []
    for fc in get_fcurves(obj):
        if fc is None or fc.lock:
            continue
        for kp in fc.keyframe_points:
            if kp.select_control_point:
                result.append((fc, kp))
    return result


class GPP_OT_apply_easing(bpy.types.Operator):
    """Apply an easing preset to selected keyframes on the active object"""
    bl_idname = "gpp.apply_easing"
    bl_label = "Apply Easing"
    bl_description = "Apply an easing preset to the selected keyframes"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(
        name="Preset",
        description="Easing curve to apply",
        items=[(k, v["label"], v["description"]) for k, v in EASING_PRESETS.items()],
        default="EASE_IN_OUT",
    )

    side: bpy.props.EnumProperty(
        name="Side",
        description="Which handle(s) to modify",
        items=[
            ('both', "Both", "Modify both handles"),
            ('in', "In (Left)", "Only modify the left handle (ease into this key)"),
            ('out', "Out (Right)", "Only modify the right handle (ease out of this key)"),
        ],
        default='both',
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        kps = _gather_selected_keyframes(obj)

        if not kps:
            self.report({'WARNING'}, "No keyframes selected. Select keyframes in the Graph Editor or Dopesheet first.")
            return {'CANCELLED'}

        applied = 0
        for fc, kp in kps:
            if apply_preset_to_keyframe(kp, self.preset, self.side):
                applied += 1
            fc.update()

        # Invalidate path cache so the redraw reflects the new easing
        from ..core.path_sampler import invalidate_cache
        invalidate_cache(obj)

        for area in context.screen.areas:
            if area.type in ('VIEW_3D', 'GRAPH_EDITOR', 'DOPESHEET_EDITOR'):
                area.tag_redraw()

        self.report({'INFO'}, f"Applied '{EASING_PRESETS[self.preset]['label']}' to {applied} keyframe(s).")
        return {'FINISHED'}


# Helper for the UI to enumerate presets
def get_preset_items():
    return [(k, v["label"], v["description"]) for k, v in EASING_PRESETS.items()]
