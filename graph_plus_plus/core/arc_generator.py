"""Arc generator — turn linear/instant rotations into beautiful bezier arcs.

This is the "Fix Arcs" operator's brain. Detects:
  1. Two adjacent rotation keyframes with LINEAR interpolation
  2. Two adjacent rotation keyframes with handles that produce near-zero
     curvature (essentially a straight slerp)

Replaces them with a bezier arc through quaternion space using a midpoint
perpendicular offset, giving the motion a smooth, weighted feel.
"""
import bpy
import math
from mathutils import Quaternion, Vector

from ..utils import quaternion_arc_handles


def find_instant_rotations(obj, threshold=0.001):
    """Find pairs of adjacent rotation keyframes that look 'instant'.

    Returns list of dicts:
        {
            'fcurve_type': 'QUATERNION' | 'EULER',
            'fcurves': [fc0, fc1, fc2, fc3],   # or [fc0,fc1,fc2] for euler
            'kp_index': int,                   # index into keyframe_points
            'frame_a': float,
            'frame_b': float,
        }

    Detection criteria:
      - Both keyframes have handle_left_type == handle_right_type == 'AUTO_CLAMPED'
        or 'VECTOR' (which produces linear-looking motion)
      - OR the difference between kp.co and kp.handle_right is below threshold
    """
    from .fcurve_access import get_rot_fcurves

    rot_type, fcs = get_rot_fcurves(obj)
    if rot_type is None or not fcs:
        return []

    # Use the first FCurve to drive the iteration (they should be in sync
    # for a single object's rotation).
    lead_fc = next((fc for fc in fcs if fc is not None), None)
    if not lead_fc or len(lead_fc.keyframe_points) < 2:
        return []

    candidates = []
    for i in range(len(lead_fc.keyframe_points) - 1):
        kp_a = lead_fc.keyframe_points[i]
        kp_b = lead_fc.keyframe_points[i + 1]

        # Check handle types
        instant_types = ("VECTOR", "AUTO_CLAMPED")
        is_instant = (
            kp_a.handle_right_type in instant_types and
            kp_b.handle_left_type in instant_types
        )

        # Also check if handles are essentially zero-length (i.e., flat)
        if not is_instant:
            dx = abs(kp_a.handle_right.x - kp_a.co.x)
            dy = abs(kp_a.handle_right.y - kp_a.co.y)
            if dx < 0.01 and dy < threshold:
                is_instant = True

        if is_instant:
            candidates.append({
                'fcurve_type': rot_type,
                'fcurves': fcs,
                'kp_index': i,
                'frame_a': kp_a.co.x,
                'frame_b': kp_b.co.x,
            })

    return candidates


def get_quaternion_at_frame(obj, frame, fcs):
    """Read the object's quaternion at a given frame from FCurves directly."""
    import bpy
    bpy.context.scene.frame_set(int(frame), subframe=frame - int(frame))
    deps = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(deps)
    return obj_eval.matrix_world.to_quaternion()


def apply_arc_to_segment(obj, segment, arc_amount=1.0):
    """Modify the handles of the keyframe pair described by `segment` to
    produce a smooth arc.

    arc_amount: 0.0 = linear (no change), 1.0 = full perpendicular offset,
                >1.0 = exaggerated.
    """
    rot_type = segment['fcurve_type']
    fcs = segment['fcurves']
    idx = segment['kp_index']

    if rot_type == "QUATERNION":
        # Get start & end quaternions from the keyframe points themselves
        # (4 channels: w, x, y, z)
        q_w_fc, q_x_fc, q_y_fc, q_z_fc = fcs
        if not all(fcs):
            return False

        kp_a_w = q_w_fc.keyframe_points[idx]
        kp_b_w = q_w_fc.keyframe_points[idx + 1]

        q_start = Quaternion((
            q_w_fc.keyframe_points[idx].co.y,
            q_x_fc.keyframe_points[idx].co.y,
            q_y_fc.keyframe_points[idx].co.y,
            q_z_fc.keyframe_points[idx].co.y,
        ))
        q_end = Quaternion((
            q_w_fc.keyframe_points[idx + 1].co.y,
            q_x_fc.keyframe_points[idx + 1].co.y,
            q_y_fc.keyframe_points[idx + 1].co.y,
            q_z_fc.keyframe_points[idx + 1].co.y,
        ))

        # Compute arc handle quaternions
        q_h_left, q_h_right = quaternion_arc_handles(q_start, q_end, arc_amount)

        # Convert to 4-tuples
        h_left = (q_h_left.w, q_h_left.x, q_h_left.y, q_h_left.z)
        h_right = (q_h_right.w, q_h_right.x, q_h_right.y, q_h_right.z)

        # Apply handles to all 4 channels
        for ch_idx, fc in enumerate(fcs):
            if fc is None:
                continue
            kp_a = fc.keyframe_points[idx]
            kp_b = fc.keyframe_points[idx + 1]

            # Set FREE handles so we can place them anywhere
            kp_a.handle_right_type = "FREE"
            kp_b.handle_left_type = "FREE"

            # Handle positions: x is the frame offset (1/3 of segment),
            # y is the channel value at the handle quaternion
            seg_len = segment['frame_b'] - segment['frame_a']
            handle_x_offset = seg_len / 3.0

            kp_a.handle_right = (
                kp_a.co.x + handle_x_offset,
                h_right[ch_idx],
            )
            kp_b.handle_left = (
                kp_b.co.x - handle_x_offset,
                h_left[ch_idx],
            )

            fc.update()

        return True

    elif rot_type == "EULER":
        # Simpler: just ease the handles to AUTO with a tangential bias
        for fc in fcs:
            if fc is None:
                continue
            kp_a = fc.keyframe_points[idx]
            kp_b = fc.keyframe_points[idx + 1]

            # Switch to aligned auto handles with slight bias
            kp_a.handle_right_type = "ALIGNED"
            kp_b.handle_left_type = "ALIGNED"

            # Compute simple symmetric handle: 1/3 of segment, biased toward
            # the average slope (smoother than VECTOR).
            seg_len = segment['frame_b'] - segment['frame_a']
            slope = (kp_b.co.y - kp_a.co.y) / max(seg_len, 0.001)
            bias = slope * seg_len / 3.0 * arc_amount

            kp_a.handle_right = (kp_a.co.x + seg_len / 3.0, kp_a.co.y + bias)
            kp_b.handle_left = (kp_b.co.x - seg_len / 3.0, kp_b.co.y - bias)

            fc.update()
        return True

    return False
