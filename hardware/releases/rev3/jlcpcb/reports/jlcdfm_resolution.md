# JLCDFM Resolution Record

This record maps the supplied PCB and SMT DFM reports to the final Rev.3 board
and manufacturing package generated on 2026-08-02.

## PCB Fabrication Checks

| Report item | Final disposition |
| --- | --- |
| Three sharp B.Cu trace corners | Replaced with short orthogonal/45-degree transitions. |
| 0.15 mm annular-ring warnings | Standard vias now use 0.60/0.20 mm or 0.65/0.25 mm copper/drill pairs. U1 thermal holes use 0.60/0.20 mm pads/drills. |
| Solder-mask openings split into multiple shapes | Duplicate USB-C mask/paste geometry was removed from pads B1, B4, B9, and B12. U1 thermal holes are tented. |
| Negative solder-mask expansion | Board-wide expansion is +0.05 mm. J1 has a -0.05 mm local correction, producing a net 1:1 opening for its fine-pitch pads rather than a negative opening. |
| Silkscreen-to-pad/hole danger and warnings | Gerber plotting subtracts solder-mask openings from both silkscreen layers. The C1 border was rerouted and nonessential J1/BZ1 outlines were moved to Fab. |
| 0.11 mm silkscreen lines | All plotted nonzero silkscreen apertures are at least 0.15 mm. |
| Four 0.60 mm plated-slot dangers | USB-C shell slots are now 0.80 mm wide and 1.70 mm long. |

## SMT Assembly Checks

| Report item | Final disposition |
| --- | --- |
| Through-hole alignment warning | USB-C locating pegs were enlarged from 0.65 mm to 0.90 mm; shell slots were widened to 0.80 mm. |
| Component clipped by board outline | Intentional for J1. The USB-C receptacle must overhang the lower edge for cable access. Do not auto-align the complete placement set in the JLCPCB viewer. |
| 0.02 mm pin-edge and lead/pad model findings | These are JLC component-model-to-footprint comparisons, not KiCad copper-clearance failures. The production footprints were retained because enlarging every flagged pad causes real copper-clearance violations. Recheck orientation and model alignment in the JLCPCB 3D viewer after upload. |

## Final Verification

- KiCad DRC: 0 errors, 0 unconnected pads.
- Remaining source warnings: two intentional rear-logo silkscreen checks.
- Production silkscreen: plotted with solder-mask subtraction enabled.
- Gerber archive: exactly 12 fabrication files.
- Drill output: minimum finished drill 0.20 mm; USB-C plated slots 0.80 mm.
- Schematic-to-PCB validation: PASS for 60 components, 37 nets, 149 connected pins, and 20 intentional no-connect pins.
- BOM/CPL validation: 15 grouped BOM lines and 44 unique top-side placements.
