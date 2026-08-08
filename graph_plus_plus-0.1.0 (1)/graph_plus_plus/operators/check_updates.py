"""Check for updates operator — fetch latest GitHub release for Toorium/GraphPlusPlus."""
import bpy
import json
import urllib.request


class GPP_OT_check_updates(bpy.types.Operator):
    """Check GitHub for a newer version of Graph++"""
    bl_idname = "gpp.check_updates"
    bl_label = "Check for Updates"
    bl_description = "Check GitHub for a newer release of Graph++"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        from .. import GPP_VERSION, GPP_GITHUB_OWNER, GPP_GITHUB_REPO

        url = f"https://api.github.com/repos/{GPP_GITHUB_OWNER}/{GPP_GITHUB_REPO}/releases/latest"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GraphPlusPlus-Blender-Addon"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            self.report({'ERROR'}, f"Failed to check updates: {e}")
            return {'CANCELLED'}

        latest_tag = data.get("tag_name", "v0.0.0").lstrip("v")
        release_url = data.get("html_url", "")
        zipball_url = data.get("zipball_url", "")

        # Store on the addon preferences so the install operator can pick it up
        prefs = context.preferences.addons.get("graph_plus_plus")
        if prefs and hasattr(prefs.preferences, "latest_version"):
            prefs.preferences.latest_version = latest_tag
            prefs.preferences.latest_release_url = release_url
            prefs.preferences.latest_zipball_url = zipball_url
            prefs.preferences.last_check = bpy.app.background_datetime_str

        # Compare versions
        try:
            cur_parts = [int(x) for x in GPP_VERSION.split(".")]
            new_parts = [int(x) for x in latest_tag.split(".")]
            is_newer = new_parts > cur_parts
        except Exception:
            is_newer = False

        if is_newer:
            self.report({'INFO'}, f"Graph++ v{latest_tag} available (you have v{GPP_VERSION}). Use 'Install Update' to apply.")
        else:
            self.report({'INFO'}, f"Graph++ is up to date (v{GPP_VERSION}).")

        return {'FINISHED'}
