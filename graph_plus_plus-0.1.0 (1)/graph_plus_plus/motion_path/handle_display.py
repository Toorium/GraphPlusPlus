"""Bezier handle display — draws tangent handles next to each keyframe
on the path so the user can grab them and shape the curve in 3D.
"""
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ..utils import PALETTE


def draw_keyframe_handles(obj, path, keyframe_positions, color=None):
    """Draw small handle indicators for each keyframe.

    For now, these are visual indicators only — the actual drag operator
    in operators/handle_drag.py implements the grab interaction.

    path: list of dicts from path_sampler.sample_object_path
    keyframe_positions: list of (frame, world_point) tuples
    """
    if not keyframe_positions:
        return

    handle_color = color or PALETTE["accent_dim"]
    line_color = PALETTE["primary_dim"]

    # Draw a small diamond at each keyframe position
    _draw_diamond_batch(keyframe_positions, handle_color)

    # Draw a thin line from each keyframe to its right handle direction
    # (using the FCurve handle slope projected into 3D via the path tangent).
    _draw_handle_lines(obj, keyframe_positions, line_color)


def _draw_diamond_batch(keyframe_positions, color):
    """Draw a small diamond (4-vertex polygon) at each keyframe position."""
    if not keyframe_positions:
        return

    # Build all vertices for all diamonds
    size = 0.04
    all_verts = []
    all_indices = []

    for i, (frame, pos) in enumerate(keyframe_positions):
        # Diamond in screen-space-ish size — we approximate with a small 3D cross
        sx = size
        sy = size
        sz = size
        base = i * 4
        all_verts.extend([
            (pos.x - sx, pos.y, pos.z),
            (pos.x + sx, pos.y, pos.z),
            (pos.x, pos.y - sy, pos.z),
            (pos.x, pos.y + sy, pos.z),
        ])
        all_indices.extend([(base + 0, base + 1), (base + 2, base + 3)])

    if not all_verts:
        return

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": all_verts}, indices=all_indices)
    shader.uniform_float("color", (*color, 1.0))
    batch.draw()


def _draw_handle_lines(obj, keyframe_positions, color):
    """Draw lines indicating handle direction at each keyframe.

    For simplicity (v0.1), we use the local path tangent at each keyframe
    to draw a short line in the direction the FCurve is heading. A future
    version will read kp.handle_right/handle_left directly and project.
    """
    if not keyframe_positions or len(keyframe_positions) < 2:
        return

    verts = []
    for i, (frame, pos) in enumerate(keyframe_positions):
        # Tangent: average of neighboring points
        if i == 0:
            tangent = (keyframe_positions[1][1] - pos).normalized()
        elif i == len(keyframe_positions) - 1:
            tangent = (pos - keyframe_positions[i - 1][1]).normalized()
        else:
            tangent = (keyframe_positions[i + 1][1] - keyframe_positions[i - 1][1]).normalized()

        length = 0.15
        verts.append((pos.x, pos.y, pos.z))
        end = pos + tangent * length
        verts.append((end.x, end.y, end.z))

    if not verts:
        return

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": verts})
    shader.uniform_float("color", (*color, 1.0))
    batch.draw()
