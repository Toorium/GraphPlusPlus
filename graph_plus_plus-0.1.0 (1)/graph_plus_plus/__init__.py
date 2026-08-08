"""
Graph++ — Smart graph editor & editable motion path for Blender 4.2+

Copyright (c) 2025 Toorium
License: GPL-3.0-or-later
"""

bl_info = {
    "name": "Graph++",
    "author": "Toorium",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N) > Graph++  |  Graph Editor > Sidebar (N) > Graph++  |  Pie: Ctrl+Shift+G",
    "description": "Smart graph editor & editable motion path. Drag the path, fix arcs, apply easing — without leaving the 3D view.",
    "doc_url": "https://github.com/Toorium/GraphPlusPlus",
    "category": "Animation",
}

# --------------------------------------------------------------------------
# Version (single source of truth — keep in sync with blender_manifest.toml)
# --------------------------------------------------------------------------
GPP_VERSION = "0.1.0"
GPP_GITHUB_OWNER = "Toorium"
GPP_GITHUB_REPO = "GraphPlusPlus"

# --------------------------------------------------------------------------
# Module imports (deferred-where-needed to avoid circular imports)
# --------------------------------------------------------------------------

# State registry — lives at the package level so all submodules can reach it.
class _GPPState:
    """Lightweight singleton holding per-object Graph++ state at runtime.

    Stored on bpy.context.scene['graph_plus_plus_state'] for persistence across
    mode swaps and undo steps. This in-memory cache is rebuilt from the scene
    property group on demand.
    """
    def __init__(self):
        self.enabled_objects = set()        # object ids enabled for path drawing
        self.colors = {}                    # object id -> (r,g,b) for multi-object tint
        self.path_cache = {}                # object id -> sampled path points (per frame)
        self.dragging = False               # True when a path-drag modal is active
        self.path_resolution = 64           # samples per keyframe segment
        self.keymap = None                  # set during register() — (keymap, keymap_item)
        self.keymap2 = None                 # set during register() — (keymap, keymap_item)


_GPP = _GPPState()


def get_state():
    """Return the package-level singleton state."""
    return _GPP


# --------------------------------------------------------------------------
# Registration order matters: lower-level modules first, UI last.
# --------------------------------------------------------------------------

def _modules_to_register():
    """Return modules in registration order. Imported lazily so a broken
    submodule doesn't block the rest of the addon from registering.
    """
    from . import utils
    from . import core
    from . import motion_path
    from . import operators
    from . import analysis
    from . import ui
    from . import updater
    return [utils, core, motion_path, operators, analysis, ui, updater]


def register():
    import bpy

    # Register PropertyGroup on Scene first so other modules can use it.
    from .ui.preferences import register_scene_properties
    register_scene_properties()

    for mod in _modules_to_register():
        if hasattr(mod, "register"):
            try:
                mod.register()
            except Exception as e:
                print(f"[Graph++] Failed to register {mod.__name__}: {e}")

    # Keymap: Ctrl+Shift+G → pie menu (in 3D view & graph editor)
    wm = bpy.context.window_manager
    if wm:
        km = wm.keyconfigs.addon.keymaps.new(name="3D View", space_type="VIEW_3D")
        kmi = km.keymap_items.new("wm.call_menu_pie", "G", "PRESS", ctrl=True, shift=True)
        kmi.properties.name = "GPP_MT_pie_main"
        # Stash for unregister
        _GPP.keymap = (km, kmi)

        km2 = wm.keyconfigs.addon.keymaps.new(name="Graph Editor", space_type="GRAPH_EDITOR")
        kmi2 = km2.keymap_items.new("wm.call_menu_pie", "G", "PRESS", ctrl=True, shift=True)
        kmi2.properties.name = "GPP_MT_pie_main"
        _GPP.keymap2 = (km2, kmi2)

    # Register draw handlers for the custom motion path.
    from .motion_path.draw import register_draw_handlers
    register_draw_handlers()

    print(f"[Graph++] v{GPP_VERSION} registered. Pie menu: Ctrl+Shift+G")


def unregister():
    import bpy

    # Unregister draw handlers first so no more callbacks fire into removed modules.
    from .motion_path.draw import unregister_draw_handlers
    try:
        unregister_draw_handlers()
    except Exception as e:
        print(f"[Graph++] unregister_draw_handlers error: {e}")

    # Keymap cleanup
    if hasattr(_GPP, "keymap"):
        km, kmi = _GPP.keymap
        km.keymap_items.remove(kmi)
        del _GPP.keymap
    if hasattr(_GPP, "keymap2"):
        km, kmi = _GPP.keymap2
        km.keymap_items.remove(kmi)
        del _GPP.keymap2

    # Unregister in reverse order.
    for mod in reversed(_modules_to_register()):
        if hasattr(mod, "unregister"):
            try:
                mod.unregister()
            except Exception as e:
                print(f"[Graph++] Failed to unregister {mod.__name__}: {e}")

    from .ui.preferences import unregister_scene_properties
    try:
        unregister_scene_properties()
    except Exception as e:
        print(f"[Graph++] unregister_scene_properties error: {e}")

    print(f"[Graph++] v{GPP_VERSION} unregistered.")


if __name__ == "__main__":
    register()
