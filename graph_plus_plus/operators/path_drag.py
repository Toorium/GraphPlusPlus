"""Path drag operator — the killer feature.

Modal operator that lets the user grab a keyframe directly on the 3D
motion path and drag it to a new position. Updates the underlying location
FCurves live, so the path reshapes in real time.

Interaction:
  1. User runs the operator (via pie menu or N-panel button)
  2. Hover the mouse over a keyframe dot on the path
  3. Click & drag — the keyframe moves in world space
  4. The FCurve's location channels are updated to match
  5. Release to confirm
"""
import bpy
import math
from bpy.types import Operator
from mathutils import Vector

from ..core.fcurve_access import (
    find_fcurve, get_loc_fcurves, commit_fcurve,
)
from ..core.path_sampler import get_keyframe_positions
from ..utils import world_to_local


class GPP_OT_path_drag(Operator):
    """Drag a keyframe directly on the 3D motion path"""
    bl_idname = "gpp.path_drag"
    bl_label = "Drag Keyframe on Path"
    bl_description = "Click and drag a keyframe dot on the 3D motion path to move it"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING', 'GRAB_CURSOR'}

    # Class-level state for the modal interaction
    _mouse_start = None
    _dragged_kp_index = None
    _drag_frame = None
    _original_values = None
    _keyframe_positions = None

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None:
            return False
        from ..motion_path.multi_object import is_enabled
        return is_enabled(obj)

    def _find_nearest_keyframe(self, context, obj, mouse_x, mouse_y):
        """Find the keyframe closest to the mouse cursor in screen space.

        Returns (frame, world_position, index) or None.
        """
        # Get the 3D region
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

        # Project each keyframe world position to screen space
        from bpy_extras import view3d_utils
        best_idx = None
        best_dist = float('inf')
        best_frame = None
        best_world = None

        for i, (frame, world_pos) in enumerate(keyframe_positions):
            screen_pos = view3d_utils.location_3d_to_region_2d(
                region, region_3d, world_pos
            )
            if screen_pos is None:
                continue
            dist = (screen_pos.x - mouse_x) ** 2 + (screen_pos.y - mouse_y) ** 2
            if dist < best_dist:
                best_dist = dist
                best_idx = i
                best_frame = frame
                best_world = world_pos

        # Threshold: 25 pixels
        if best_dist > 25 ** 2:
            return None

        return (best_frame, best_world, best_idx)

    def invoke(self, context, event):
        obj = context.active_object

        nearest = self._find_nearest_keyframe(context, obj, event.mouse_region_x, event.mouse_region_y)
        if nearest is None:
            self.report({'WARNING'}, "No keyframe near cursor. Hover over a keyframe dot on the path.")
            return {'CANCELLED'}

        self._drag_frame, world_pos, idx = nearest
        self._dragged_kp_index = idx

        # Store original keyframe values for cancel/undo
        loc_fcurves = get_loc_fcurves(obj)
        self._original_values = []
        for fc in loc_fcurves:
            if fc is None:
                self._original_values.append(None)
                continue
            # Find the keyframe point matching this frame
            kp = None
            for k in fc.keyframe_points:
                if abs(k.co.x - self._drag_frame) < 0.5:
                    kp = k
                    break
            if kp is None:
                self._original_values.append(None)
            else:
                self._original_values.append((fc, kp, kp.co.y))

        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, f"Dragging keyframe at frame {int(self._drag_frame)}")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        obj = context.active_object
        if obj is None:
            return {'CANCELLED'}

        if event.type == 'ESC':
            # Cancel — restore original values
            self._restore_original(obj)
            return {'CANCELLED'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            # Commit
            self._commit(obj)
            return {'FINISHED'}

        if event.type == 'MOUSEMOVE':
            self._update_drag(context, obj, event.mouse_region_x, event.mouse_region_y)

        return {'RUNNING_MODAL'}

    def _update_drag(self, context, obj, mouse_x, mouse_y):
        """Project the mouse onto a camera-facing plane through the keyframe's
        original world position, then write the new local-space location back
        to the FCurves.
        """
        # Find region & 3d region
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

        # Original world position (used as the plane origin)
        if not self._original_values:
            return

        # Get original world position from cached keyframe positions
        keyframe_positions = get_keyframe_positions(obj)
        if self._dragged_kp_index >= len(keyframe_positions):
            return
        original_world = keyframe_positions[self._dragged_kp_index][1]

        # Raycast from mouse into the 3D scene onto a plane perpendicular
        # to the camera direction, passing through original_world.
        view_vector = view3d_utils.region_2d_to_vector_3d(region, region_3d, (mouse_x, mouse_y))
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, region_3d, (mouse_x, mouse_y))

        # Plane normal = camera view direction (looking INTO the screen)
        cam_forward = -region_3d.view_rotation @ Vector((0, 0, -1))

        # Plane: dot(P - original_world, cam_forward) = 0
        denom = view_vector.dot(cam_forward)
        if abs(denom) < 1e-6:
            return

        t = (original_world - ray_origin).dot(cam_forward) / denom
        new_world = ray_origin + view_vector * t

        # Convert to local space
        new_local = world_to_local(obj, new_world)

        # Write to FCurves
        loc_fcurves = get_loc_fcurves(obj)
        for ax, fc in enumerate(loc_fcurves):
            if fc is None:
                continue
            # Find the keyframe point matching self._drag_frame
            for kp in fc.keyframe_points:
                if abs(kp.co.x - self._drag_frame) < 0.5:
                    kp.co.y = new_local[ax]
                    break
            commit_fcurve(fc)

        # Update scene frame to trigger redraw
        context.scene.frame_set(int(context.scene.frame_current))
        for area in context.screen.areas:
            if area.type in ('VIEW_3D', 'GRAPH_EDITOR', 'DOPESHEET_EDITOR'):
                area.tag_redraw()

    def _restore_original(self, obj):
        """Restore original keyframe values (cancel)."""
        if not self._original_values:
            return
        for entry in self._original_values:
            if entry is None:
                continue
            fc, kp, original_y = entry
            kp.co.y = original_y
            commit_fcurve(fc)

    def _commit(self, obj):
        """Final commit — values already written. Just report."""
        self.report({'INFO'}, f"Keyframe at frame {int(self._drag_frame)} updated.")
        # Clear state
        self._original_values = None
        self._dragged_kp_index = None
        self._drag_frame = None
