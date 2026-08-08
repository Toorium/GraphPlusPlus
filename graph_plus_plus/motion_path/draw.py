"""Main GPU draw handler for Graph++ motion paths.

Registered as a post-view draw callback on the 3D view space. Iterates
all objects with Graph++ enabled, samples their world-space trajectory,
and draws:
  - Velocity-colored line strip (the path itself)
  - Keyframe diamond markers
  - Handle direction indicators
"""
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ..utils import PALETTE, velocity_color
from ..core.path_sampler import sample_object_path, get_path_segments, get_keyframe_positions
from .multi_object import iter_enabled_objects, get_tint
from .handle_display import draw_keyframe_handles


_DRAW_HANDLER = None


def _draw_object_path(obj):
    """Draw the Graph++ path for a single object."""
    tint = get_tint(obj)

    # Sample the path
    samples_per_segment = 8
    try:
        path = sample_object_path(obj, samples_per_segment=samples_per_segment)
    except Exception as e:
        print(f"[Graph++] path sampling failed for {obj.name}: {e}")
        return

    if len(path) < 2:
        return

    segments = get_path_segments(path)
    if not segments:
        return

    # Build colored line strip
    verts = []
    colors = []
    for p0, p1, v_t in segments:
        # Mix velocity color with the per-object tint so multiple objects
        # remain distinguishable but still convey speed.
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

    # Draw the path itself
    try:
        shader = gpu.shader.from_builtin('SMOOTH_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": verts, "color": colors})
        batch.draw()
    except Exception as e:
        print(f"[Graph++] path draw error: {e}")
        return

    # Draw keyframe markers
    try:
        keyframe_positions = get_keyframe_positions(obj)
        if keyframe_positions:
            _draw_keyframe_dots(keyframe_positions, tint)
            draw_keyframe_handles(obj, path, keyframe_positions, tint)
    except Exception as e:
        print(f"[Graph++] keyframe draw error: {e}")


def _draw_keyframe_dots(keyframe_positions, color):
    """Draw small filled circles at each keyframe position.

    Uses a polygon approximation since GPU module doesn't have a built-in
    circle primitive. Draws 12-sided polygons.
    """
    import math
    sides = 12
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
        # Triangle fan around the center
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
    """The actual callback registered with the space."""
    # Bail out gracefully if no enabled objects
    try:
        enabled = list(iter_enabled_objects())
    except Exception:
        return

    if not enabled:
        return

    # Ensure we're in a state where GPU drawing is valid
    try:
        gpu.state.line_width_set(2.0)
        gpu.state.point_size_set(6.0)
    except Exception:
        pass

    for obj in enabled:
        try:
            _draw_object_path(obj)
        except Exception as e:
            print(f"[Graph++] draw error on {getattr(obj, 'name', '?')}: {e}")

    try:
        gpu.state.line_width_set(1.0)
    except Exception:
        pass


def register_draw_handlers():
    """Register the post-view draw callback on every 3D view space."""
    import blf

    global _DRAW_HANDLER

    if _DRAW_HANDLER is not None:
        return

    # Find the VIEW_3D space type
    space_view_3d = bpy.types.SpaceView3D
    _DRAW_HANDLER = space_view_3d.draw_handler_add(_draw_callback, (), 'WINDOW', 'POST_VIEW')


def unregister_draw_handlers():
    """Remove the draw callback."""
    global _DRAW_HANDLER

    if _DRAW_HANDLER is None:
        return

    try:
        bpy.types.SpaceView3D.draw_handler_remove(_DRAW_HANDLER, 'WINDOW')
    except Exception as e:
        print(f"[Graph++] draw_handler_remove error: {e}")
    _DRAW_HANDLER = None
