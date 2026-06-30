# CAD Design

When the task involves 3D models, mechanical parts, robotics, or hardware:

1. **Install CAD Skills** if not present: `npx skills install earthtojake/text-to-cad`
2. Use **build123d** (Python) as the primary authoring engine for parametric CAD.
3. Export formats by use case:
   - **STEP** (.step) — machining, assemblies, interchange
   - **STL** (.stl) — 3D printing
   - **3MF** — multi-material print prep
   - **URDF/SDF** — robotics simulation
4. Workflow: sketch parameters → build geometry → validate dimensions → export → verify file exists.
5. Name parts descriptively (`PLANETARY_GEAR_ASSEMBLY.step`, not `output.step`).
6. For assemblies, document mate relationships in comments and acceptance criteria.
7. Run a quick geometry sanity check before marking the slice complete (file size > 0, valid header).

## Registry conventions

- CAD modules: `CadPart`, `GearAssembly`, `RobotModel`
- Export paths: `exports/` or `cad/` subdirectory
- Env: `CAD_EXPORT_DIR` if the project uses one

## Integration with build pipeline

- Slice contracts must list exact output filenames.
- Validation: confirm exported files exist and are non-empty.
- Dependencies: simulation slices depend on URDF/SDF from modeling slices.
