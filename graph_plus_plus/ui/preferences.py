"""Preferences & scene properties for Graph++.

Defines:
  - GraphPlusPreferences (AddonPreferences) — colors, GitHub URL, update state
  - Scene-level boolean property on Object: gpp_enabled (registered as RNA property)
"""
import bpy
from bpy.props import (
    StringProperty, BoolProperty, FloatProperty, FloatVectorProperty,
    IntProperty, EnumProperty,
)

from .. import GPP_VERSION, GPP_GITHUB_OWNER, GPP_GITHUB_REPO


# --------------------------------------------------------------------------
# Addon Preferences
# --------------------------------------------------------------------------
class GraphPlusPreferences(bpy.types.AddonPreferences):
    bl_idname = "graph_plus_plus"

    # Display
    path_resolution: IntProperty(
        name="Path Resolution",
        description="Number of samples per keyframe segment (higher = smoother but slower)",
        default=8,
        min=2,
        max=64,
    )

    path_line_width: FloatProperty(
        name="Path Line Width",
        description="Line width for the motion path in pixels",
        default=2.0,
        min=0.5,
        max=8.0,
    )

    keyframe_marker_size: FloatProperty(
        name="Keyframe Marker Size",
        description="Size of keyframe dots on the path",
        default=0.05,
        min=0.01,
        max=0.5,
    )

    primary_color: FloatVectorProperty(
        name="Primary Color",
        description="Main Graph++ brand color (desaturated purple recommended)",
        subtype='COLOR',
        default=(0.545, 0.482, 0.710),
        min=0.0, max=1.0,
    )

    # Auto-update
    auto_check_updates: BoolProperty(
        name="Auto-check for updates on startup",
        description="Query GitHub for new releases when Blender starts (may add ~1s startup delay)",
        default=True,
    )

    github_owner: StringProperty(
        name="GitHub Owner",
        description="GitHub repository owner for update checks",
        default=GPP_GITHUB_OWNER,
    )

    github_repo: StringProperty(
        name="GitHub Repo",
        description="GitHub repository name for update checks",
        default=GPP_GITHUB_REPO,
    )

    latest_version: StringProperty(
        name="Latest Available Version",
        default="",
    )

    latest_release_url: StringProperty(
        name="Latest Release URL",
        default="",
    )

    latest_zipball_url: StringProperty(
        name="Latest Zipball URL",
        default="",
    )

    staged_zip_path: StringProperty(
        name="Staged Update Zip",
        description="Path to a downloaded update zip, staged for install on next restart",
        default="",
    )

    last_check: StringProperty(
        name="Last Update Check",
        default="",
    )

    def draw(self, context):
        layout = self.layout

        # Version info
        box = layout.box()
        box.label(text=f"Graph++ v{GPP_VERSION}", icon='INFO')
        box.label(text=f"Repo: github.com/{GPP_GITHUB_OWNER}/{GPP_GITHUB_REPO}")

        # Display settings
        box = layout.box()
        box.label(text="Display", icon='COLOR')
        box.prop(self, "path_resolution")
        box.prop(self, "path_line_width")
        box.prop(self, "keyframe_marker_size")
        box.prop(self, "primary_color")

        # Auto-update
        box = layout.box()
        box.label(text="Auto-Update", icon='URL')
        box.prop(self, "auto_check_updates")
        box.prop(self, "github_owner")
        box.prop(self, "github_repo")

        if self.latest_version:
            col = box.column()
            col.label(text=f"Latest available: v{self.latest_version}", icon='WORLD')
            if self.staged_zip_path:
                col.label(text=f"Staged: {self.staged_zip_path}", icon='FILE_TICK')
            else:
                col.label(text="Click 'Check for Updates' in the N-panel to download.", icon='INFO')


# --------------------------------------------------------------------------
# Scene-level Object property registration
# --------------------------------------------------------------------------
def register_scene_properties():
    """Register the gpp_enabled RNA property on Object."""
    bpy.types.Object.gpp_enabled = bpy.props.BoolProperty(
        name="Graph++ Path Enabled",
        description="Toggle Graph++ motion path drawing for this object",
        default=False,
    )


def unregister_scene_properties():
    try:
        del bpy.types.Object.gpp_enabled
    except Exception:
        pass


# --------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------
classes = (
    GraphPlusPreferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[Graph++] unregister error for {cls.__name__}: {e}")
