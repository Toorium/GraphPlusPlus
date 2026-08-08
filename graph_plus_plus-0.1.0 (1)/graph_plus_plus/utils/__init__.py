"""Graph++ utility helpers — math, color palette, GPU shapes.

All colors in Graph++ follow a desaturated purple-forward palette so the
overlay reads as part of Blender's dark UI rather than competing with it.
"""
import math
from mathutils import Vector, Quaternion, Matrix


# --------------------------------------------------------------------------
# Brand palette — muted/desaturated purple forward
# --------------------------------------------------------------------------
PALETTE = {
    # Primary brand purple (desaturated, mid-lightness)
    "primary":          (0.545, 0.482, 0.710),  # ~#8B7BB5
    "primary_dim":      (0.404, 0.357, 0.525),  # darker for inactive paths
    "primary_bright":   (0.682, 0.620, 0.890),  # for selected/hovered

    # Accent — soft lavender-pink for keyframe marks & handles
    "accent":           (0.760, 0.620, 0.760),
    "accent_dim":       (0.560, 0.455, 0.560),

    # Velocity gradient stops (cool→warm but muted, never neon)
    "vel_min":          (0.392, 0.475, 0.690),  # slow = soft blue
    "vel_low":          (0.425, 0.620, 0.690),  # cyan-green
    "vel_mid":          (0.700, 0.690, 0.520),  # muted yellow-green
    "vel_high":         (0.780, 0.565, 0.470),  # muted orange
    "vel_max":          (0.745, 0.420, 0.470),  # muted red-pink

    # UI greys
    "ui_bg":            (0.122, 0.122, 0.137),
    "ui_text":          (0.890, 0.890, 0.890),
    "ui_warn":          (0.810, 0.620, 0.320),
}


def lerp_color(c1, c2, t):
    """Linear interpolation between two RGB tuples (each 0..1)."""
    t = max(0.0, min(1.0, t))
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def velocity_color(t):
    """Map normalized velocity (0..1) to a muted gradient color.

    Uses 5 stops: blue → cyan-green → yellow-green → orange → red-pink.
    Returns RGB tuple in 0..1 range suitable for GPU shaders.
    """
    t = max(0.0, min(1.0, t))
    if t < 0.25:
        return lerp_color(PALETTE["vel_min"], PALETTE["vel_low"], t / 0.25)
    elif t < 0.50:
        return lerp_color(PALETTE["vel_low"], PALETTE["vel_mid"], (t - 0.25) / 0.25)
    elif t < 0.75:
        return lerp_color(PALETTE["vel_mid"], PALETTE["vel_high"], (t - 0.50) / 0.25)
    else:
        return lerp_color(PALETTE["vel_high"], PALETTE["vel_max"], (t - 0.75) / 0.25)


# --------------------------------------------------------------------------
# Bezier math — cubic bezier evaluation & derivative
# --------------------------------------------------------------------------

def cubic_bezier(p0, p1, p2, p3, t):
    """Evaluate cubic bezier at t. Inputs/outputs are 3-vectors."""
    u = 1.0 - t
    return (
        p0 * (u * u * u) +
        p1 * (3 * u * u * t) +
        p2 * (3 * u * t * t) +
        p3 * (t * t * t)
    )


def cubic_bezier_derivative(p0, p1, p2, p3, t):
    """Derivative of cubic bezier — used for velocity calc."""
    u = 1.0 - t
    return (
        (p1 - p0) * (3 * u * u) +
        (p2 - p1) * (6 * u * t) +
        (p3 - p2) * (3 * t * t)
    )


# --------------------------------------------------------------------------
# Quaternion arc helpers — for "fix instant rotation into beautiful arc"
# --------------------------------------------------------------------------

def quaternion_arc_handles(q_start, q_end, arc_amount=1.0):
    """Given two end rotations (quaternions), compute intermediate control
    quaternions that describe a smooth arc through slerp space.

    arc_amount: 0.0 = straight slerp (linear in quaternion space),
                1.0 = full arc (handle direction perpendicular to slerp path),
                >1.0 = exaggerated overshoot.
    Returns (q_handle_left, q_handle_right) suitable for bezier evaluation.
    """
    # Slerp midpoint
    q_mid = q_start.slerp(q_end, 0.5)

    # Compute "perpendicular" rotation by rotating the midpoint slightly
    # around an axis orthogonal to the rotation plane.
    delta = q_end.rotation_difference(q_start)
    axis = Vector((0, 0, 1))
    # Use delta's axis if available, else fallback
    try:
        axis = Vector(delta.axis)
    except Exception:
        pass

    # Offset rotation: rotate q_mid around the perpendicular axis
    offset_angle = math.radians(15.0 * arc_amount)
    q_offset = Quaternion(axis, offset_angle)

    q_h_left = q_mid * q_offset
    q_h_right = q_mid * q_offset.inverted()

    return q_h_left, q_h_right


# --------------------------------------------------------------------------
# Vector / matrix helpers
# --------------------------------------------------------------------------

def world_to_local(obj, world_point):
    """Transform a world-space point to obj local space."""
    if obj.matrix_world:
        return obj.matrix_world.inverted() @ world_point
    return world_point


def local_to_world(obj, local_point):
    """Transform a local-space point to world space."""
    return obj.matrix_world @ local_point


# --------------------------------------------------------------------------
# Misc helpers
# --------------------------------------------------------------------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def format_frame(f):
    """Format a frame number for on-screen display (e.g. 'f24')."""
    return f"f{int(round(f))}"


def is_github_url(url):
    return "github.com" in url.lower() or "api.github.com" in url.lower()
