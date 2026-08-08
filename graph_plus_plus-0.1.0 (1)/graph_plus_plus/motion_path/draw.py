"""Main GPU draw handler for Graph++ motion paths — OPTIMIZED version.

Key optimizations:
  1. Uses cached path data (see core/path_sampler.py)
  2. Throttles to max 30fps (configurable)
  3. Wraps EVERYTHING in try/except — never crash Blender
  4. Skips objects with too many samples
  5. Caches the enabled-objects list
  6. Uses batched GPU draws (single batch per object, not per segment)
"""
import bpy
import gpu
import time
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ..utils import PALETTE, velocity_color
from ..core.path_sampler import sample_object_path, get_path_segments, get_keyframe_positions
from .multi_object import iter_enabled_objects, get_tint
from .handle_display import draw_keyframe_handles


_DRAW_HANDLER = None
_LAST_DRAW_TIME = 0.0
_DRAW_THROTTLE = 1.0 / 30.0  # max 30 redraws per second


def _draw_object_path(obj):
    """Draw the Graph++ path for a single object. NEVER raises."""
    try:
        tint = get_tint(obj)

        # Sample the path (uses cache)
        path = sample_object_path(obj, samples_per_segment=6, use_cache=True)

        if len(path) < 2:
            return

        # Safety cap — if path is absurdly long, skip drawing
        if len(path) > 500:
            print(f"[Graph++] Path for {obj.name} has {len(path)} samples — skipping draw (too long).")
            return

        segments = get_path_segments(path)
        if not segments:
            return

        # Build colored line strip — SINGLE BATCH per object
        verts = []
        colors = []
        for p0, p1, v_t in segments:
            vcol = velocity_color(v_t)
            mixed = (
                vcol[0] * 0.7 + tint[0] * 0.3,
                vcol[1] * 0.7 + tint[1] * 0.3,
                vcol[2] * 0.7 + tint[2] * 0.3,
            )
            verts.append((p0.x, p0.y, p0.z))
            verts.append((p1.x, p1.y, p1.z))
            colors.append((*mixed, 1.0))
            colors.append((*mixed, 1.0))

        if not verts:
            return

        # Draw the path itself — single batch
        try:
            shader = gpu.shader.from_builtin('SMOOTH_COLOR')
            batch = batch_for_shader(shader, 'LINES', {"pos": verts, "color": colors})
            batch.draw()
        except Exception as e:
            print(f"[Graph++] path draw error on {obj.name}: {e}")
            return

        # Draw keyframe markers
        try:
            keyframe_positions = get_keyframe_positions(obj)
            if keyframe_positions:
                _draw_keyframe_dots(keyframe_positions, tint)
                # Only draw handles if we have few keyframes (perf safeguard)
                if len(keyframe_positions) <= 50:
                    draw_keyframe_handles(obj, path, keyframe_positions, tint)
        except Exception as e:
            print(f"[Graph++] keyframe draw error on {obj.name}: {e}")

    except Exception as e:
        # Last-resort catch — NEVER let a draw error propagate to Blender
        print(f"[Graph++] draw_object_path error on {getattr(obj, 'name', '?')}: {e}")


def _draw_keyframe_dots(keyframe_positions, color):
    """Draw small circles at each keyframe position — SINGLE BATCH."""
    import math

    # Cap the number of keyframe dots we draw
    if len(keyframe_positions) > 200:
        keyframe_positions = keyframe_positions[:200]

    sides = 8  # octagon — fewer verts than 12-sided, still looks round
    radius = 0.05
    all_verts = []
    all_colors = []
    indices = []

    for i, (frame, pos) in enumerate(keyframe_positions):
        base = i * sides
        for s in range(sides):
            angle = 2 * math.pi * s / sides
            all_verts.append((
                pos.x + radius * math.cos(angle),
                pos.y + radius * math.sin(angle),
                pos.z,
            ))
            all_colors.append((*color, 1.0))
        for s in range(sides):
            indices.append((base + s, base + (s + 1) % sides))

    if not all_verts:
        return

    try:
        shader = gpu.shader.from_builtin('SMOOTH_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": all_verts, "color": all_colors}, indices=indices)
        batch.draw()
    except Exception as e:
        print(f"[Graph++] keyframe dot draw error: {e}")


def _draw_callback():
    """The actual callback registered with the space. NEVER raises."""
    global _LAST_DRAW_TIME

    # ----- Throttle: max 30fps -----
    now = time.time()
    if now - _LAST_DRAW_TIME < _DRAW_THROTTLE:
        return
    _LAST_DRAW_TIME = now

    try:
        enabled = list(iter_enabled_objects())
    except Exception:
        return

    if not enabled:
        return

    # Safety cap — don't draw more than 20 objects at once
    if len(enabled) > 20:
        print(f"[Graph++] {len(enabled)} objects have path enabled — capping to first 20 for performance.")
        enabled = enabled[:20]

    # Set line width once
    try:
        gpu.state.line_width_set(2.0)
        gpu.state.point_size_set(6.0)
    except Exception:
        pass

    for obj in enabled:
        _draw_object_path(obj)

    try:
        gpu.state.line_width_set(1.0)
    except Exception:
        pass


def register_draw_handlers():
    """Register the post-view draw callback on every 3D view space."""
    global _DRAW_HANDLER

    if _DRAW_HANDLER is not None:
        return

    # Also register the depsgraph handler for cache invalidation
    from ..core.path_sampler import register_depsgraph_handler
    register_depsgraph_handler()

    space_view_3d = bpy.types.SpaceView3D
    _DRAW_HANDLER = space_view_3d.draw_handler_add(_draw_callback, (), 'WINDOW', 'POST_VIEW')


def unregister_draw_handlers():
    """Remove the draw callback."""
    global _DRAW_HANDLER

    if _DRAW_HANDLER is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_DRAW_HANDLER, 'WINDOW')
        except Exception as e:
            print(f"[Graph++] draw_handler_remove error: {e}")
        _DRAW_HANDLER = None

    # Unregister depsgraph handler
    try:
        from ..core.path_sampler import unregister_depsgraph_handler
        unregister_depsgraph_handler()
    except Exception:
        pass

    # Clear cache
    try:
        from ..core.path_sampler import invalidate_cache
        invalidate_cache()
    except Exception:
        pass
