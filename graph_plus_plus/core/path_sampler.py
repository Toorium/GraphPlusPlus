"""Path sampler — build a world-space trajectory from object FCurves.

Samples the object's evaluated location across the action's frame range
and returns a list of (frame, world_position, velocity) tuples.
"""
import bpy
import math
from mathutils import Vector


def sample_object_path(obj, frame_start=None, frame_end=None, samples_per_segment=8):
    """Sample obj's world location across the action range.

    Returns a list of dicts:
        {
            'frame': float,
            'point': Vector,         # world-space position
            'velocity': float,       # |dP/dt| in units/frame
            'is_keyframe': bool,     # True if this frame is a keyframe
        }

    Resolution is controlled by samples_per_segment: more samples = smoother
    path color gradient, but slower draw.
    """
    from .fcurve_access import get_action

    action = get_action(obj)
    if not action:
        return []

    # Determine frame range
    if frame_start is None or frame_end is None:
        fs, fe = action.frame_range
        if frame_start is None:
            frame_start = int(fs)
        if frame_end is None:
            frame_end = int(fe)

    if frame_end <= frame_start:
        return []

    # Collect all keyframe frames on the location FCurves
    from .fcurve_access import find_fcurve
    keyframe_frames = set()
    for ax in range(3):
        fc = find_fcurve(obj, "location", ax)
        if fc:
            for kp in fc.keyframe_points:
                keyframe_frames.add(round(kp.co.x))
    # Also include current frame if not in set
    keyframe_frames.add(int(bpy.context.scene.frame_current))

    # Build sample frames — denser between keyframes
    sorted_keys = sorted(keyframe_frames)
    sample_frames = []

    if not sorted_keys:
        # No keyframes — uniform sample
        step = max(1, int((frame_end - frame_start) / 64))
        sample_frames = list(range(frame_start, frame_end + 1, step))
    else:
        # Ensure range bounds
        if sorted_keys[0] > frame_start:
            sorted_keys.insert(0, frame_start)
        if sorted_keys[-1] < frame_end:
            sorted_keys.append(frame_end)

        for i in range(len(sorted_keys) - 1):
            f0 = sorted_keys[i]
            f1 = sorted_keys[i + 1]
            for s in range(samples_per_segment):
                t = s / samples_per_segment
                sample_frames.append(f0 + (f1 - f0) * t)
        sample_frames.append(sorted_keys[-1])

    # Evaluate object location at each sample frame
    deps = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(deps)
    prev_point = None
    prev_frame = None

    path = []
    for f in sample_frames:
        # Set scene frame for evaluation
        # NOTE: We use obj_eval.matrix_world which is updated by depsgraph.
        # For correct per-frame evaluation, we set the scene frame and update.
        bpy.context.scene.frame_set(int(f), subframe=f - int(f))
        try:
            p = obj_eval.matrix_world.translation.copy()
        except Exception:
            continue

        v = 0.0
        if prev_point is not None and f > prev_frame:
            dt = f - prev_frame
            v = (p - prev_point).length / dt

        path.append({
            'frame': f,
            'point': p,
            'velocity': v,
            'is_keyframe': int(round(f)) in keyframe_frames,
        })

        prev_point = p
        prev_frame = f

    return path


def get_path_segments(path):
    """Convert flat path list into [(p0, p1, color_t), ...] segments for drawing.

    color_t is the normalized velocity for the segment (0..1) based on the
    max velocity in the path.
    """
    if len(path) < 2:
        return []

    max_v = max((p['velocity'] for p in path), default=1.0)
    if max_v <= 1e-6:
        max_v = 1.0

    segments = []
    for i in range(len(path) - 1):
        p0 = path[i]
        p1 = path[i + 1]
        v_avg = (p0['velocity'] + p1['velocity']) * 0.5
        segments.append((p0['point'], p1['point'], v_avg / max_v))

    return segments


def get_keyframe_positions(obj):
    """Return list of (frame, world_position) for every keyframe on the
    object's location FCurves. Used for drawing keyframe dots on the path.
    """
    from .fcurve_access import find_fcurve

    # Find all keyframe frames across the 3 location axes
    frame_set = set()
    for ax in range(3):
        fc = find_fcurve(obj, "location", ax)
        if fc:
            for kp in fc.keyframe_points:
                frame_set.add(round(kp.co.x))

    if not frame_set:
        return []

    # Evaluate world position at each keyframe frame
    deps = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(deps)

    positions = []
    for f in sorted(frame_set):
        bpy.context.scene.frame_set(f)
        try:
            p = obj_eval.matrix_world.translation.copy()
            positions.append((float(f), p))
        except Exception:
            continue

    return positions
