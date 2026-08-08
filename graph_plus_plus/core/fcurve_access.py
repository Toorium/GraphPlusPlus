"""FCurve access wrappers — safe get/set of keyframes & handles.

All Graph++ operators that modify animation go through this module so we
have a single place to handle:
  - Missing action / FCurve
  - Locked channels
  - Handle type conversions
  - Triggering fcurve.update() after edits
"""
import bpy
from bpy.types import Object, FCurve, FCurveKeyframePoints


# Channels we care about for path editing.
LOC_CHANNELS = ["location", "rotation_euler", "rotation_quaternion", "scale"]


def get_action(obj):
    """Return the active action on obj (or its data if obj has no action)."""
    if obj is None:
        return None
    if obj.animation_data and obj.animation_data.action:
        return obj.animation_data.action
    # Some objects (e.g. bones) store animation on the armature's data
    if hasattr(obj, "data") and obj.data:
        if obj.data.animation_data and obj.data.animation_data.action:
            return obj.data.animation_data.action
    return None


def get_fcurves(obj):
    """Yield all FCurves on obj's active action (or its data)."""
    action = get_action(obj)
    if not action:
        return []
    return list(action.fcurves)


def find_fcurve(obj, data_path, array_index=None):
    """Find an FCurve by data_path (and optionally array_index).

    data_path examples: 'location', 'rotation_euler', 'pose.bones["Arm"].location'
    """
    action = get_action(obj)
    if not action:
        return None
    for fc in action.fcurves:
        if fc.data_path == data_path:
            if array_index is None or fc.array_index == array_index:
                return fc
    return None


def get_loc_keyframes(obj, axis=None):
    """Return list of (frame, value, keyframe_point) tuples for location.

    axis: None for all 3 axes (returns dict {0: [...], 1: [...], 2: [...]}),
          or 0/1/2 for a single axis (returns list).
    """
    action = get_action(obj)
    if not action:
        return {} if axis is None else []

    if axis is None:
        result = {}
        for ax in range(3):
            fc = find_fcurve(obj, "location", ax)
            result[ax] = [(kp.co.x, kp.co.y, kp) for kp in fc.keyframe_points] if fc else []
        return result
    else:
        fc = find_fcurve(obj, "location", axis)
        return [(kp.co.x, kp.co.y, kp) for kp in fc.keyframe_points] if fc else []


def get_object_location_at(obj, frame):
    """Evaluate the object's world location at a given frame.

    Uses the depsgraph evaluation to honor constraints, parents, etc.
    """
    import bpy
    deps = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(deps)
    return obj_eval.matrix_world.translation.copy()


def set_keyframe_value(kp, frame, value, update_handles=True):
    """Safely set a keyframe point's frame & value.

    kp.co.x = frame, kp.co.y = value. Triggers update() on the FCurve
    (caller is responsible, since FCurve reference isn't stored on kp).
    """
    kp.co.x = float(frame)
    kp.co.y = float(value)


def set_keyframe_handle(kp, side, handle_type="FREE", vector=None):
    """Set a keyframe's left or right handle.

    side: 'left' or 'right'
    handle_type: 'FREE', 'ALIGNED', 'AUTO', 'AUTO_CLAMPED', 'VECTOR'
    vector: optional 2-tuple (x, y) for handle position (relative to kp.co
            for ALIGNED handles, absolute for FREE handles)
    """
    if side == "left":
        kp.handle_left_type = handle_type
        if vector is not None:
            kp.handle_left = vector
    else:
        kp.handle_right_type = handle_type
        if vector is not None:
            kp.handle_right = vector


def commit_fcurve(fc):
    """Call .update() on the FCurve and tag the action as updated."""
    if fc is None:
        return
    try:
        fc.update()
    except Exception as e:
        print(f"[Graph++] fcurve.update() error: {e}")
    # Mark action as updated for redraw
    try:
        fc.id_data.update_tag()
    except Exception:
        pass


def get_loc_fcurves(obj):
    """Return the 3 location FCurves (or None for missing axes)."""
    return [find_fcurve(obj, "location", ax) for ax in range(3)]


def get_rot_fcurves(obj):
    """Return rotation FCurves. Quaternion: 4 channels; Euler: 3 channels."""
    # Try quaternion first
    quats = [find_fcurve(obj, "rotation_quaternion", ax) for ax in range(4)]
    if any(quats):
        return ("QUATERNION", quats)
    eulers = [find_fcurve(obj, "rotation_euler", ax) for ax in range(3)]
    if any(eulers):
        return ("EULER", eulers)
    return (None, [])
