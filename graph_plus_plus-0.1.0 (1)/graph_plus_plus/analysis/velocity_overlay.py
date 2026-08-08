"""Velocity/Acceleration overlay drawn inside the Graph Editor — OPTIMIZED.

Uses the cached path sampler (no frame_set calls). Throttled to 15fps
since this is a secondary visualization.
"""
import bpy
import gpu
import time
from gpu_extras.batch import batch_for_shader

from ..utils import PALETTE, velocity_color
from ..core.path_sampler import sample_object_path
from ..core.velocity import compute_speed_series, compute_acceleration_series


_DRAW_HANDLER = None
_LAST_DRAW_TIME = 0.0
_DRAW_THROTTLE = 1.0 / 15.0  # max 15 redraws per second — this is a secondary viz


def _draw_overlay():
    """Draw a small velocity/acceleration mini-graph. NEVER raises."""
    global _LAST_DRAW_TIME

    # Throttle
    now = time.time()
    if now - _LAST_DRAW_TIME < _DRAW_THROTTLE:
        return
    _LAST_DRAW_TIME = now

    try:
        context = bpy.context
        obj = context.active_object
        if obj is None:
            return

        # Only draw if Graph++ is enabled on this object
        from ..motion_path.multi_object import is_enabled
        if not is_enabled(obj):
            return

        # Sample the path (cached — fast)
        path = sample_object_path(obj, samples_per_segment=4, use_cache=True)
        if len(path) < 2:
            return

        speed = compute_speed_series(path)
        accel = compute_acceleration_series(path)

        region = context.region
        if region is None or region.type != 'WINDOW':
            return

        w = region.width
        h = region.height

        panel_w = min(280, w - 40)
        panel_h = 80
        panel_x = w - panel_w - 20
        panel_y = 20

        # Background quad
        bg_verts = [
            (panel_x, panel_y),
            (panel_x + panel_w, panel_y),
            (panel_x + panel_w, panel_y + panel_h),
            (panel_x, panel_y + panel_h),
        ]
        bg_indices = [(0, 1, 2), (0, 2, 3)]

        try:
            shader_uni = gpu.shader.from_builtin('UNIFORM_COLOR')
            bg_batch = batch_for_shader(shader_uni, 'TRIS', {"pos": bg_verts}, indices=bg_indices)
            shader_uni.uniform_float("color", (*PALETTE["ui_bg"], 0.85))
            bg_batch.draw()
        except Exception:
            return

        # Plot speed as a colored line graph
        if speed:
            max_speed = max((v for _, v in speed), default=1.0) or 1.0
            verts = []
            colors = []
            for i, (frame, v) in enumerate(speed):
                t = i / max(1, len(speed) - 1)
                x = panel_x + 10 + t * (panel_w - 20)
                normalized = v / max_speed
                y = panel_y + 10 + normalized * (panel_h - 20)
                verts.append((x, y))
                c = velocity_color(normalized)
                colors.append((*c, 1.0))

            if len(verts) >= 2:
                try:
                    shader_smooth = gpu.shader.from_builtin('SMOOTH_COLOR')
                    line_batch = batch_for_shader(shader_smooth, 'LINE_STRIP', {"pos": verts, "color": colors})
                    line_batch.draw()
                except Exception:
                    pass

        # Plot acceleration as a thin overlay
        if accel:
            max_a = max((abs(v) for _, v in accel), default=1.0) or 1.0
            verts = []
            for i, (frame, v) in enumerate(accel):
                t = i / max(1, len(accel) - 1)
                x = panel_x + 10 + t * (panel_w - 20)
                normalized = v / max_a
                y = panel_y + panel_h / 2 + normalized * (panel_h / 2 - 10)
                verts.append((x, y))

            if len(verts) >= 2:
                try:
                    shader_uni2 = gpu.shader.from_builtin('UNIFORM_COLOR')
                    accel_batch = batch_for_shader(shader_uni2, 'LINE_STRIP', {"pos": verts})
                    shader_uni2.uniform_float("color", (*PALETTE["accent_dim"], 0.6))
                    accel_batch.draw()
                except Exception:
                    pass

    except Exception as e:
        # NEVER let the overlay crash the graph editor
        print(f"[Graph++] velocity_overlay error: {e}")


def register():
    global _DRAW_HANDLER
    if _DRAW_HANDLER is None:
        _DRAW_HANDLER = bpy.types.SpaceGraphEditor.draw_handler_add(
            _draw_overlay, (), 'WINDOW', 'POST_PIXEL'
        )


def unregister():
    global _DRAW_HANDLER
    if _DRAW_HANDLER is not None:
        try:
            bpy.types.SpaceGraphEditor.draw_handler_remove(_DRAW_HANDLER, 'WINDOW')
        except Exception:
            pass
        _DRAW_HANDLER = None
