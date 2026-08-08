"""Handle drag operator — drag a bezier handle to shape the curve in 3D.

This is the second half of "the path IS the editor": in addition to
dragging keyframe points, the user can drag the handle direction lines
to change the slope/curvature of the segment leading into/out of a
keyframe.

For v0.1, this operator handles the right handle of a keyframe. Dragging
the right handle updates kp.handle_right for all 3 location axes.
"""
import bpy
import math
from bpy.types import Operator
from mathutils import Vector

from ..core.fcurve_access import get_loc_fcurves, commit_fcurve
from ..core.path_sampler import get_keyframe_positions
from ..utils import world_to_local


class GPP_OT_handle_drag(Operator):
    """Drag a bezier handle on the 3D path to shape the curve"""
    bl_idname = "gpp.handle_drag"
    bl_label = "Drag Handle on Path"
    bl_description = "Drag a handle direction line to adjust the curve's slope"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    _drag_frame = None
    _drag_side = None  # 'left' or 'right'
    _original_handles = None

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None:
            return False
        from ..motion_path.multi_object import is_enabled
        return is_enabled(obj)

    def _find_nearest_handle(self, context, obj, mouse_x, mouse_y):
        """Find the handle end closest to the mouse.

        Each keyframe has a left & right handle direction line. We compute
        the world position of each handle end and pick the closest one
        within a threshold.

        Returns (frame, side, world_pos) or None.
        """
        region = None
        region_3d = None
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                region = area.regions.get('WINDOW')
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        region_3d = space.region_3d
                        break
                break

        if region is None or region_3d is None:
            return None

        keyframe_positions = get_keyframe_positions(obj)
        if not keyframe_positions:
            return None

        from bpy_extras import view3d_utils

        # For each keyframe, compute left & right handle world positions.
        # The handle direction in 3D = path tangent at the keyframe, scaled
        # by the FCurve's handle slope.
        loc_fcurves = get_loc_fcurves(obj)

        best = None
        best_dist = float('inf')

        for i, (frame, world_pos) in enumerate(keyframe_positions):
            # Tangent direction (3D)
            if i == 0:
                tangent_right = (keyframe_positions[1][1] - world_pos).normalized()
                tangent_left = -tangent_right
            elif i == len(keyframe_positions) - 1:
                tangent_left = (keyframe_positions[i - 1][1] - world_pos).normalized()
                tangent_right = -tangent_left
            else:
                tangent_left = (keyframe_positions[i - 1][1] - world_pos).normalized()
                tangent_right = (keyframe_positions[i + 1][1] - world_pos).normalized()

            # Compute average handle magnitude across the 3 loc FCurves
            right_mag = 0.0
            left_mag = 0.0
            right_count = 0
            left_count = 0
            for fc in loc_fcurves:
                if fc is None:
                    continue
                for kp in fc.keyframe_points:
                    if abs(kp.co.x - frame) < 0.5:
                        right_mag += abs(kp.handle_right.x - kp.co.x)
                        left_mag += abs(kp.handle_left.x - kp.co.x)
                        right_count += 1
                        left_count += 1
                        break
            if right_count > 0:
                right_mag /= right_count
            if left_count > 0:
                left_mag /= left_count

            # Handle end positions in world space
            # Scale the 3D handle to a reasonable visual size for picking.
            visual_scale = 0.15
            right_end = world_pos + tangent_right * visual_scale
            left_end = world_pos + tangent_left * visual_scale

            for side, end in (('right', right_end), ('left', left_end)):
                screen_pos = view3d_utils.location_3d_to_region_2d(region, region_3d, end)
                if screen_pos is None:
                    continue
                dist = (screen_pos.x - mouse_x) ** 2 + (screen_pos.y - mouse_y) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best = (frame, side, end)

        if best_dist > 25 ** 2:
            return None

        return best

    def invoke(self, context, event):
        obj = context.active_object

        nearest = self._find_nearest_handle(context, obj, event.mouse_region_x, event.mouse_region_y)
        if nearest is None:
            self.report({'WARNING'}, "No handle near cursor. Hover over a handle direction line on the path.")
            return {'CANCELLED'}

        self._drag_frame, self._drag_side, original_world = nearest

        # Store original handles for cancel
        loc_fcurves = get_loc_fcurves(obj)
        self._original_handles = []
        for fc in loc_fcurves:
            if fc is None:
                self._original_handles.append(None)
                continue
            kp = None
            for k in fc.keyframe_points:
                if abs(k.co.x - self._drag_frame) < 0.5:
                    kp = k
                    break
            if kp is None:
                self._original_handles.append(None)
            else:
                if self._drag_side == 'right':
                    self._original_handles.append((fc, kp, kp.handle_right_type, tuple(kp.handle_right)))
                else:
                    self._original_handles.append((fc, kp, kp.handle_left_type, tuple(kp.handle_left)))

        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, f"Dragging {self._drag_side} handle at frame {int(self._drag_frame)}")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        obj = context.active_object
        if obj is None:
            return {'CANCELLED'}

        if event.type == 'ESC':
            self._restore_original()
            return {'CANCELLED'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._commit()
            return {'FINISHED'}

        if event.type == 'MOUSEMOVE':
            self._update_drag(context, obj, event.mouse_region_x, event.mouse_region_y)

        return {'RUNNING_MODAL'}

    def _update_drag(self, context, obj, mouse_x, mouse_y):
        """Update the handle position based on mouse movement.

        For v0.1: we don't move the handle's frame offset (kp.handle_right.x
        stays the same). Instead, we change kp.handle_right.y to slope-match
        the new tangent in 3D. The slope is computed from the projected
        mouse position vs the keyframe's original world position.
        """
        # Invalidate path cache so the redraw reflects the drag in real time
        from ..core.path_sampler import invalidate_cache
        invalidate_cache(obj)
        region = None
        region_3d = None
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                region = area.regions.get('WINDOW')
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        region_3d = space.region_3d
                        break
                break

        if region is None or region_3d is None:
            return

        from bpy_extras import view3d_utils

        # Get the original world position of the keyframe
        keyframe_positions = get_keyframe_positions(obj)
        original_world = None
        for frame, pos in keyframe_positions:
            if abs(frame - self._drag_frame) < 0.5:
                original_world = pos
                break
        if original_world is None:
            return

        # Project mouse onto camera-facing plane through original_world
        view_vector = view3d_utils.region_2d_to_vector_3d(region, region_3d, (mouse_x, mouse_y))
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, region_3d, (mouse_x, mouse_y))
        cam_forward = -region_3d.view_rotation @ Vector((0, 0, -1))

        denom = view_vector.dot(cam_forward)
        if abs(denom) < 1e-6:
            return

        t = (original_world - ray_origin).dot(cam_forward) / denom
        new_world = ray_origin + view_vector * t

        # New 3D tangent direction (from keyframe to mouse position)
        new_tangent_world = new_world - original_world
        new_tangent_local = world_to_local(obj, new_world) - world_to_local(obj, original_world)

        # Determine the next/prev keyframe frame to compute handle x offset
        loc_fcurves = get_loc_fcurves(obj)
        lead_fc = next((fc for fc in loc_fcurves if fc is not None), None)
        if lead_fc is None:
            return

        sorted_kps = sorted(lead_fc.keyframe_points, key=lambda k: k.co.x)
        current_idx = None
        for i, kp in enumerate(sorted_kps):
            if abs(kp.co.x - self._drag_frame) < 0.5:
                current_idx = i
                break
        if current_idx is None:
            return

        if self._drag_side == 'right':
            if current_idx + 1 >= len(sorted_kps):
                return  # no next keyframe
            next_frame = sorted_kps[current_idx + 1].co.x
            handle_x_offset = (next_frame - self._drag_frame) / 3.0
            new_handle_x = self._drag_frame + handle_x_offset
        else:
            if current_idx - 1 < 0:
                return  # no prev keyframe
            prev_frame = sorted_kps[current_idx - 1].co.x
            handle_x_offset = (self._drag_frame - prev_frame) / 3.0
            new_handle_x = self._drag_frame - handle_x_offset

        # Scale the local tangent to match the handle x offset
        # We want the handle's y-component (per axis) to reflect the slope
        # implied by the new 3D tangent direction.
        # For each axis, the new slope = new_tangent_local[axis] / handle_x_offset
        for ax, fc in enumerate(loc_fcurves):
            if fc is None:
                continue
            for kp in fc.keyframe_points:
                if abs(kp.co.x - self._drag_frame) < 0.5:
                    # Set handle to FREE so we can place it anywhere
                    if self._drag_side == 'right':
                        kp.handle_right_type = "FREE"
                        # Slope = (new_y - kp.co.y) / handle_x_offset
                        # => new_y = kp.co.y + slope * handle_x_offset
                        # But slope in FCurve space = new_tangent_local[ax] / dt_in_frames
                        # For visual feel, we map the local tangent direction
                        # directly to the handle y delta.
                        new_y = kp.co.y + new_tangent_local[ax] * 0.3  # scale for visual feel
                        kp.handle_right = (new_handle_x, new_y)
                    else:
                        kp.handle_left_type = "FREE"
                        new_y = kp.co.y - new_tangent_local[ax] * 0.3
                        kp.handle_left = (new_handle_x, new_y)
                    break
            commit_fcurve(fc)

        for area in context.screen.areas:
            if area.type in ('VIEW_3D', 'GRAPH_EDITOR', 'DOPESHEET_EDITOR'):
                area.tag_redraw()

    def _restore_original(self):
        if not self._original_handles:
            return
        for entry in self._original_handles:
            if entry is None:
                continue
            fc, kp, handle_type, handle_pos = entry
            if self._drag_side == 'right':
                kp.handle_right_type = handle_type
                kp.handle_right = handle_pos
            else:
                kp.handle_left_type = handle_type
                kp.handle_left = handle_pos
            commit_fcurve(fc)

    def _commit(self):
        self.report({'INFO'}, f"Handle at frame {int(self._drag_frame)} updated.")
        self._original_handles = None
        self._drag_frame = None
        self._drag_side = None
