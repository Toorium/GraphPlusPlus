"""Color LUT — velocity → muted gradient color.

Single source of truth for path coloring. Re-exports from utils for
convenience so motion_path submodules don't import across packages.
"""
from ..utils import velocity_color, PALETTE


__all__ = ["velocity_color", "PALETTE"]
