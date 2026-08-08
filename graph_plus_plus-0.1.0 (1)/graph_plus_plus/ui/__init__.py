"""UI registration — combines preferences, N-panel, and pie menu."""
from . import preferences, n_panel, pie_menu


def register():
    preferences.register()
    n_panel.register()
    pie_menu.register()


def unregister():
    pie_menu.unregister()
    n_panel.unregister()
    preferences.unregister()
