# BMW E46 2.8L Drift Exhaust — 3D Model

Parametric 3D model of a **valved X-pipe exhaust** for the **BMW E46 328i (M52TU 2.8L inline-6)**, tuned for **drift** with a **deep, menacing** tone.

## What's in the box

| File | Purpose |
|------|---------|
| `generate_exhaust.py` | Python generator — edit `ExhaustSpec` and re-run |
| `exhaust-e46.scad` | OpenSCAD source for parametric edits |
| `preview.html` | Browser 3D viewer (loads GLB) |
| `output/bmw_e46_28l_drift_exhaust.stl` | Single mesh for 3D printing / CAD import |
| `output/bmw_e46_28l_drift_exhaust.obj` | Wavefront OBJ |
| `output/bmw_e46_28l_drift_exhaust.glb` | GLB with scene graph (web / Blender) |
| `output/manifest.json` | Dimensions and mesh stats |

## Exhaust layout

```
[Cyl 1-3 runners]──┐                              ┌──[Valve]──[Muffler]──╮ 4" tip
                    ├──[3" primary]──╳ X-pipe ╳──┤
[Cyl 4-6 runners]──┘                              └──[Valve]──[Muffler]──╯ 4" tip
        ▲                                                    ▲
   6-2-1 collectors                              Butterfly bypass (open = drift)
```

### Sound design (why it's deep & menacing)

| Choice | Rationale |
|--------|-----------|
| **3" (76.2 mm) primaries** | Lower resonance frequency on a 2.8L I6; fuller tone without choking flow at drift RPM |
| **X-pipe @ 55°** | Strong pulse scavenging between banks — classic raspy-deepest BMW burble |
| **Resonator delete** | Removes the factory mid muffler that kills low-end growl |
| **Straight-through mufflers** | Perforated core — volume control without strangling the note |
| **Butterfly valves (open)** | Full bypass for track/drift; close for stealth street if needed |
| **4" rolled tips, 18° turn-out** | Aggressive visual + slight tone broadening at the tail |

### Dimensions

| Component | Size |
|-----------|------|
| Header runners | 2.0" OD (50.8 mm) |
| Collectors → primaries | 3.0" OD (76.2 mm) |
| X-pipe crossover angle | 55° |
| Mufflers | 320 mm length, 130 mm OD, 3" perforated core |
| Tips | 4.0" OD (101.6 mm), 140 mm, 18° outward cant |
| Bank spacing | 380 mm (L/R collector centres) |
| Valves | 95 mm body, butterfly disc shown **88° open** (drift mode) |

> **Note:** This is a **concept / visualisation model** for fabrication planning. Final fitment on an E46 requires measuring your specific subframe, diff, and driveshaft clearance. M52 non-Vanos and M52TU header flanges differ — verify flange pattern before cutting metal.

## Quick start

```bash
cd models/bmw-e46-drift-exhaust
pip install -r requirements.txt
python3 generate_exhaust.py
```

Open `preview.html` in a browser (serve locally if needed):

```bash
python3 -m http.server 8080
# → http://localhost:8080/preview.html
```

### OpenSCAD

```bash
openscad -o output/exhaust.scad.stl exhaust-e46.scad
```

## Customisation

Edit `ExhaustSpec` in `generate_exhaust.py`:

```python
@dataclass
class ExhaustSpec:
    primary_od: float = 76.2      # bump to 3.25" for even deeper tone
    x_cross_angle_deg: float = 55.0
    tip_od: float = 101.6
    tip_angle_deg: float = 18.0
    # ...
```

For a louder drift setup: increase `primary_od` to 82.5 (3.25"), set valve `open_angle_deg` to 90°, shorten `muffler_length` to 200 mm or replace mufflers with straight pipe sections.

For a slightly quieter street-drifting compromise: use 2.75" primaries and 3.5" tips — still deep, less drone at cruise.

## Import into CAD

- **Blender:** File → Import → glTF 2.0 (`.glb`)
- **Fusion 360 / SolidWorks:** Import `.stl` or `.obj`, scale is 1 unit = 1 mm
- **Meshmixer / Cura:** Use `.stl` for print preview (not intended as a bolt-on part without modification)

## E46 2.8L reference

- Engine: BMW M52TU, 2.8 L, 24-valve DOHC inline-6
- Stock power: ~193 hp — drift builds often run headers + full exhaust + tune
- Factory exhaust: dual cats → resonator → rear mufflers; this model deletes the resonator and replaces rear section with valved straight-through design

---

*Generated for drift use. Weld quality, hanger placement, and heat shielding are your responsibility — this model covers the pipe geometry only.*
