"""Multi-object overlay manager — OPTIMIZED version.

Caches the enabled-objects list with a short TTL so we don't iterate
all scene.objects on every redraw.
"""
import bpy
import random
import time
from ..utils import PALETTE


_PER_OBJECT_TINTS = {}

# Cache for iter_enabled_objects()
# (timestamp, [(cam_z, obj), ...])
_ENABLED_CACHE = None
_ENABLED_CACHE_TIME = 0.0
_ENABLED_CACHE_TTL = 0.5  # seconds


def is_enabled(obj):
    """Check if Graph++ path drawing is enabled for this object."""
    if obj is None:
        return False
    # Try the RNA property first (registered on Object), fall back to dict
    try:
        return bool(obj.gpp_enabled)
    except (AttributeError, TypeError):
        return bool(obj.get("gpp_enabled", False))


def set_enabled(obj, enabled):
    """Enable/disable Graph++ path drawing for an object."""
    if obj is None:
        return
    try:
        obj.gpp_enabled = bool(enabled)
    except (AttributeError, TypeError):
        obj["gpp_enabled"] = bool(enabled)

    # Assign a tint if newly enabled
    if enabled and obj.as_pointer() not in _PER_OBJECT_TINTS:
        _PER_OBJECT_TINTS[obj.as_pointer()] = _make_tint()

    # Invalidate the enabled-objects cache
    global _ENABLED_CACHE, _ENABLED_CACHE_TIME
    _ENABLED_CACHE = None
    _ENABLED_CACHE_TIME = 0.0


def _make_tint():
    """Generate a desaturated tint near the primary purple."""
    bases = [
        PALETTE["primary"],
        PALETTE["primary_dim"],
        PALETTE["accent"],
        PALETTE["vel_low"],
        PALETTE["vel_min"],
    ]
    base = random.choice(bases)
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
    sorted back-to-front by camera-space Z.

    CACHED — only recomputes every 0.5s.
    """
    global _ENABLED_CACHE, _ENABLED_CACHE_TIME

    scene = bpy.context.scene
    if not scene:
        return

    # Check cache
    now = time.time()
    if _ENABLED_CACHE is not None and (now - _ENABLED_CACHE_TIME) < _ENABLED_CACHE_TTL:
        for _, obj in _ENABLED_CACHE:
            # Verify the object still exists (user may have deleted it)
            try:
                obj.name
                yield obj
            except (ReferenceError, AttributeError):
                continue
        return

    # Rebuild cache
    region_3d = None
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    region_3d = space.region_3d
                    break
            break

    cam_forward = None
    view_location = None
    if region_3d is not None:
        try:
            cam_forward = region_3d.view_matrix.to_3x3().transposed().col[2].copy()
            view_location = region_3d.view_location.copy()
        except Exception:
            cam_forward = None

    candidates = []
    for obj in scene.objects:
        try:
            if is_enabled(obj):
                if cam_forward is not None and view_location is not None:
                    try:
                        cam_z = (obj.matrix_world.translation - view_location).dot(cam_forward)
                    except Exception:
                        cam_z = 0.0
                else:
                    cam_z = 0.0
                candidates.append((cam_z, obj))
        except (ReferenceError, AttributeError):
            continue

    # Sort back-to-front: higher cam_z = further from camera = drawn first
    candidates.sort(key=lambda c: -c[0])

    _ENABLED_CACHE = candidates
    _ENABLED_CACHE_TIME = now

    for _, obj in candidates:
        yield obj


def invalidate_enabled_cache():
    """Force the enabled-objects cache to rebuild on next call."""
    global _ENABLED_CACHE, _ENABLED_CACHE_TIME
    _ENABLED_CACHE = None
    _ENABLED_CACHE_TIME = 0.0
