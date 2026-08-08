"""Updater package — GitHub release check & staged download.

The actual operators live in operators/check_updates.py and
operators/install_update.py. This module just provides helpers and
the startup auto-check hook.
"""
import bpy

from .. import GPP_VERSION, GPP_GITHUB_OWNER, GPP_GITHUB_REPO


def startup_check():
    """Called during addon registration if auto_check_updates is enabled.

    Performs a non-blocking fetch to GitHub's releases API and stores the
    result in addon preferences.
    """
    try:
        prefs = bpy.context.preferences.addons.get("graph_plus_plus")
        if not prefs or not prefs.preferences:
            return
        if not prefs.preferences.auto_check_updates:
            return
    except Exception:
        return

    # Defer to the operator (which has proper error handling)
    try:
        bpy.ops.gpp.check_updates()
    except Exception as e:
        print(f"[Graph++] Auto-update check failed: {e}")


def register():
    # Defer the check by 2 seconds so Blender finishes loading first.
    try:
        bpy.app.timers.register(startup_check, first_interval=2.0)
    except Exception as e:
        print(f"[Graph++] timer registration error: {e}")


def unregister():
    try:
        if bpy.app.timers.is_registered(startup_check):
            bpy.app.timers.unregister(startup_check)
    except Exception:
        pass
