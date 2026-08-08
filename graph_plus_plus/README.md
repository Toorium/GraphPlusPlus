# Graph++

**A smart graph editor & editable motion path for Blender 4.2+**

Graph++ replaces Blender's default motion path with a fully editable, velocity-colored, multi-object overlay. Drag keyframes and bezier handles directly on the 3D path — no more jumping to the graph editor. Plus one-click smart tweaks: fix instant rotations into beautiful arcs, apply easing presets, add anticipation & follow-through.

## Features (v0.1.0 — MVP)

### The killer feature: the path IS the editor
- **Drag Keyframe on Path** — click & drag a keyframe dot in the 3D viewport; the location FCurves update live
- **Drag Handle on Path** — grab a bezier handle direction line to shape the curve's slope in 3D

### Custom motion path
- Velocity-based color gradient (cool = slow, warm = fast) — muted, never neon
- Keyframe diamond markers along the path
- Per-object tint for multi-object overlays with depth sorting
- Desaturated purple-forward palette to match Blender's dark UI

### Smart tweaks
- **Fix Arcs** — detects instant/linear rotations, replaces with smooth bezier arcs through quaternion space
- **Easing Presets** — 10 presets: ease in/out, back, elastic, bounce, linear
- **Add Anticipation** — auto-insert lead-in keyframes opposite to motion direction
- **Add Follow-Through** — overshoot + decaying settle keys

### Analysis
- **Velocity/Acceleration overlay** — mini-graph in the Graph Editor sidebar showing speed and accel of the active object

### UI
- N-panel "Graph++" tab in both View3D and Graph Editor
- Pie menu on `Ctrl+Shift+G` (rebindable in Preferences > Keymap)
- Toggle path on/off per object

### Auto-update
- Checks GitHub (`Toorium/GraphPlusPlus`) for new releases
- Downloads and stages the zip; user installs via Preferences > Extensions > Install from Disk

## Installation

### From source (development)
1. Clone or download this repo
2. Zip the `graph_plus_plus` folder (so the zip contains `blender_manifest.toml` at its root)
3. In Blender 4.2+: Edit > Preferences > Extensions > Install from Disk

### From release
1. Download the latest `.zip` from [Releases](https://github.com/Toorium/GraphPlusPlus/releases)
2. In Blender 4.2+: Edit > Preferences > Extensions > Install from Disk

## Usage

1. Select an animated object
2. Open the N-panel (press `N`) > **Graph++** tab
3. Click **Toggle Path** to enable the motion path overlay
4. Use the buttons or `Ctrl+Shift+G` pie menu to:
   - Drag keyframes / handles on the path
   - Apply smart tweaks
   - Apply easing presets

## Keymap

| Action | Default | Rebindable |
|--------|---------|------------|
| Open Graph++ pie menu | `Ctrl+Shift+G` | Yes — Preferences > Keymap > Graph++ |

## Technical

- **Blender 4.2+ Extensions format** (`blender_manifest.toml`)
- **Algorithmic only** — zero external Python dependencies
- **GPU module only** (no deprecated `bgl`)
- **Permissions**: `files` (update download), `network` (GitHub API)

## Roadmap

- [ ] Bone/pose support (currently object-level only)
- [ ] Direct FCurve handle projection (currently uses path tangent)
- [ ] Beat-sync keyframes to audio waveform
- [ ] Curve compare (left/right diff)
- [ ] Hot-swap auto-update (no Blender restart required)

## License

GPL-3.0-or-later

## Author

**Toorium** — [github.com/Toorium](https://github.com/Toorium)
