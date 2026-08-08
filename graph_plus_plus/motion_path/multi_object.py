"""Multi-object overlay manager.

Tracks which objects have Graph++ enabled, assigns per-object tints,
and provides depth-sorted iteration for back-to-front drawing.
"""
import bpy
import random
from ..utils import PALETTE, lerp_color


_PER_OBJECT_TINTS = {}


def is_enabled(obj):
    """Check if Graph++ path drawing is enabled for this object."""
    if obj is None:
        return False
    return obj.get("gpp_enabled", False) or bool(obj.gpp_enabled if hasattr(obj, "gpp_enabled") else False)


def set_enabled(obj, enabled):
    """Enable/disable Graph++ path drawing for an object."""
    if obj is None:
        return
    try:
        obj.gpp_enabled = bool(enabled)
    except Exception:
        obj["gpp_enabled"] = bool(enabled)

    if enabled and obj.as_pointer() not in _PER_OBJECT_TINTS:
        # Assign a slight hue variation around the primary palette so
        # multiple objects remain distinguishable without going neon.
        _PER_OBJECT_TINTS[obj.as_pointer()] = _make_tint()


def _make_tint():
    """Generate a desaturated tint near the primary purple, with small
    hue shifts toward lavender, mauve, or cool blue-grey.
    """
    bases = [
        PALETTE["primary"],          # primary purple
        PALETTE["primary_dim"],      # darker purple
        PALETTE["accent"],           # soft lavender-pink
        PALETTE["vel_low"],          # cool teal
        PALETTE["vel_min"],          # soft blue
    ]
    base = random.choice(bases)
    # Slight variation
    jitter = lambda v: max(0.0, min(1.0, v + random.uniform(-0.05, 0.05)))
    return (jitter(base[0]), jitter(base[1]), jitter(base[2]))


def get_tint(obj):
    """Get the per-object tint color (RGB tuple 0..1)."""
    if obj is None:
        return PALETTE["primary"]
    pid = obj.as_pointer()
    if pid not in _PER_OBJECT_TINTS:
        _PER_OBJECT_TINTS[pid] = _make_tint()
    return _PER_OBJECT_TINTS[pid]


def iter_enabled_objects():
    """Yield all objects in the current scene with Graph++ enabled,
    sorted back-to-front by average camera-space Z.
    """
    scene = bpy.context.scene
    if not scene:
        return

    # Get camera direction
    region_3d = None
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    region_3d = space.region_3d
                    break
            break

    cam_forward = None
    if region_3d is not None:
        cam_forward = region_3d.view_matrix.to_3x3().transposed().col[2].copy()

    candidates = []
    for obj in scene.objects:
        if is_enabled(obj):
            # Compute average Z in camera space (approx: use object origin)
            if cam_forward is not None:
                cam_z = (obj.matrix_world.translation - region_3d.view_location).dot(cam_forward)
            else:
                cam_z = 0.0
            candidates.append((cam_z, obj))

    # Sort back-to-front: higher cam_z = further from camera = drawn first
    candidates.sort(key=lambda c: -c[0])
    for _, obj in candidates:
        yield obj
