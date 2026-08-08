"""Install update operator — download & extract the latest GitHub release zip.

For Blender 4.2+ Extensions, the proper way to "install" an updated addon
is to download the zip and use bpy.ops.extensions.repo_install_from_url
(or the user manually drops it in Preferences > Extensions). Since the
files are locked while Blender is running, this operator:
  1. Downloads the zip to a temp location
  2. Saves the path to preferences
  3. Prompts the user to restart Blender (with the zip staged for install)

A future version could write to a "staging" directory and have the addon
swap files on next Blender launch via the registration lifecycle.
"""
import bpy
import os
import tempfile
import urllib.request


class GPP_OT_install_update(bpy.types.Operator):
    """Download the latest Graph++ release zip and stage it for install"""
    bl_idname = "gpp.install_update"
    bl_label = "Install Update"
    bl_description = "Download the latest release zip and prepare it for installation (Blender restart required)"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        prefs = context.preferences.addons.get("graph_plus_plus")
        if not prefs or not prefs.preferences:
            return False
        return bool(getattr(prefs.preferences, "latest_zipball_url", ""))

    def execute(self, context):
        from .. import GPP_GITHUB_OWNER, GPP_GITHUB_REPO, GPP_VERSION

        prefs = context.preferences.addons.get("graph_plus_plus").preferences
        zipball_url = prefs.latest_zipball_url
        latest_tag = prefs.latest_version

        if not zipball_url:
            self.report({'ERROR'}, "No update URL cached. Run 'Check for Updates' first.")
            return {'CANCELLED'}

        # Download to temp dir
        tmp_dir = tempfile.gettempdir()
        zip_path = os.path.join(tmp_dir, f"graph_plus_plus_{latest_tag}.zip")

        try:
            req = urllib.request.Request(zipball_url, headers={"User-Agent": "GraphPlusPlus-Blender-Addon"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(zip_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
        except Exception as e:
            self.report({'ERROR'}, f"Download failed: {e}")
            return {'CANCELLED'}

        # Stage the path in preferences
        prefs.staged_zip_path = zip_path

        self.report({'INFO'}, f"Update downloaded to {zip_path}. Restart Blender and install via Preferences > Extensions > Install from Disk.")
        return {'FINISHED'}
