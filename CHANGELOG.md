# Changelog

All notable changes to this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Worked-example data in `data/examples/` (one trial per stance) so users can test the pipeline without downloading the full Figshare archive.
- MATLAB parity port of the Python pipeline (`src/matlab/`).

## [0.4.0] — 2026-05-15

### Added
- **`kds.loader_kinetic`** module — reads Bertec force-platform TSV files exported by Qualisys QTM. Handles the 11-column variant (subjects `ID003`–`ID004`) and the 9-column variant (subjects `ID005`–`ID014`) transparently; resolves the `KUK→KOK` acquisition-time typo for `ID009`; parses the 26-line metadata header including 4-corner plate geometry in the laboratory frame.
- **`kds.export_kinetic_timeseries`** module — exports one CSV per trial with the unprocessed force-platform records of both Bertec 3 and Bertec 4 platforms side-by-side at the native 1000 Hz sampling.
  - 192 trial CSVs total: 180 dynamic at 9 000 frames × 20 columns + 12 STATIC at variable frames × 20 columns.
  - Each CSV carries `frame`, `time_s`, and a 9-column block per platform (`FP3_Fx_N`, `FP3_Fy_N`, `FP3_Fz_N`, `FP3_Mx_Nmm`, `FP3_My_Nmm`, `FP3_Mz_Nmm`, `FP3_COPx_mm`, `FP3_COPy_mm`, `FP3_COPz_mm` and the same six for FP4).
  - **No filtering, no platform combination, no descriptors, no demographic metadata.** Force, moment, and COP released exactly as exported by Qualisys QTM in the laboratory frame.
  - Five trials with only one platform that fired are retained, with the absent platform's columns filled with `NaN`s. The full record is in the released QC report.
  - Auxiliary tables: `kinetic_qc_report.csv` (192 rows × 12 cols) flags per-trial completeness; `kinetic_plate_corners.csv` (1 516 rows × 7 cols) provides the laboratory-frame corner coordinates of each plate per trial.
  - CLI: `python -m kds.export_kinetic_timeseries --data-root <path> --output-dir <out>`.
- `data/timeseries_kinetic_raw/README.md` — schema documentation including the explicit Bertec sign convention (negative `Fz` under body weight; moments are *free* moments about the plate centre).

### Notes
- Body-weight cross-check (sanity, not used by the pipeline): for participant `ID003`, the mean of `FP3_Fz + FP4_Fz` across a representative `ZEN` trial is −687.78 N versus an expected −678.85 N from declared body mass — a 1.3 % offset consistent with day-of-acquisition mass variation and footwear.
- The 322 MB per-trial kinetic CSV archive is **not** committed to Git for the same reason as the kinematic archive: it is regenerable from the released pipeline and is intended for the Figshare release at the dataset DOI [10.6084/m9.figshare.32288943](https://doi.org/10.6084/m9.figshare.32288943). The QC report and plate-corners table are small (~30 KB total) and *are* tracked in the repo so the QC record is auditable without downloading the bulk data.

## [0.3.0] — 2026-05-15

### Added
- **`kds.export_timeseries`** module — extracts per-trial pure kinematic time-series CSVs (no aggregated descriptors, no demographic columns) from the raw Theia3D C3D archive.
  - One CSV per trial, 98 columns each: `frame`, `time_s`, linear position of the 19 segment origins (m), whole-body COM (m, sex-specific inertia looked up internally), and Cardan/Euler joint angles of the 12 ISB joints (deg).
  - Dynamic trials (180 files): `data/timeseries_raw/<ID>_<BASE>_T<N>_kinematics.csv` × 1620 frames.
  - STATIC references (9 files): `data/timeseries_raw/static/<ID>_STATIC_T1_kinematics.csv` × variable frames.
  - Default input is the **raw** `*_pose_0.c3d` (use `--filtered` for the Theia-filtered variant).
  - CLI: `python -m kds.export_timeseries --data-root <path> --output-dir <out>`.
- `data/timeseries_raw/README.md` — schema documentation for the per-trial CSVs.

### Notes
- The 260 MB per-trial CSV archive is **not** committed to Git; it is regenerable from the released pipeline. The full archive is intended for the Figshare release at the dataset DOI [10.6084/m9.figshare.32288943](https://doi.org/10.6084/m9.figshare.32288943). The schema README is tracked in the repo so that the layout is discoverable without downloading the archive.

## [0.2.0] — 2026-05-14

### Added
- **Open Python processing pipeline** (`src/python/kds/`) — 8 modules implementing the full kinematic stream:
  - `loader.py` reads Theia3D C3D files (19 rigid-body segments stored as 4×4 homogeneous transforms at 180 Hz) and the Visual3D POS export; resolves the acquisition-time `KUK→KOK` naming typo for `ID009` automatically; discovers all 189 trials of the dataset (180 dynamic + 9 STATIC).
  - `demographics.py` records the canonical demographic table of the 12 participants (sex, age, height, mass, BMI, style, modality, level, years of practice, training frequency, dominant guard).
  - `kinematics_linear.py` computes segment-origin trajectories, whole-body centre of mass (gender-specific, using the Theia3D-stored inertial parameters), linear velocities, and linear accelerations (with optional 6 Hz pre-differentiation smoothing).
  - `kinematics_angular.py` computes 12 joint angles by Cardan/Euler decomposition of the relative segment rotations following ISB recommendations (Wu et al., 2002, 2005): hip, knee, ankle bilaterally (Z–X–Y); shoulder, elbow bilaterally (Y–X–Z); pelvis vs world and trunk vs pelvis (Z–X–Y).
  - `strike_detection.py` auto-detects the `gyaku-tsuki` strike instant from hand end-effector speed; selects the hand with the higher peak; marks onset and return at 10 % of peak.
  - `descriptors.py` computes 180+ per-trial descriptors in the pre-strike (1–3 s) and post-strike (6–9 s) windows: COM mean and sway (ML/AP/Z range, RMS, path length), joint angle means and ROMs (36 axes per window), base-of-support width/depth/area/centroid, and cross-pipeline COM offset against Visual3D.
  - `batch.py` CLI driver (`python -m kds.batch --data-root <path> --output-dir <out>`) runs the full pipeline over all 189 trials and emits five outputs.
  - `plots.py` generates four diagnostic figures from the summary CSVs.
- **Pipeline outputs** (`data/processed_summary/`) — released alongside the pipeline:
  - `KDS_summary_all_trials.csv` (180 rows × 181 columns) — full descriptor panel per dynamic trial.
  - `KDS_summary_static.csv` (9 rows × 12 columns) — STATIC reference descriptors.
  - `KDS_subject_means.csv` (36 rows) — per-subject means by base.
  - `KDS_qc_report.csv` (189 rows) — per-trial QC flags.
  - `pipeline_metadata.json` — pipeline version + run timestamp.
- **Diagnostic figures** (`figures/`) — `strike_timing_distribution.png`, `bos_by_stance.png`, `com_descriptors_by_stance.png`, `subject_means_com_height.png`.
- **Project configuration** — `pyproject.toml` declaring dependencies (`ezc3d`, `numpy`, `scipy`, `pandas`, `matplotlib`) for `pip install -e .` reproducibility.

### Findings worth flagging for users
- **Trial completeness**: 180/180 dynamic trials and 9 STATIC reference trials processed without error; subjects `ID003`, `ID004`, `ID005` do not carry a STATIC reference (acquired as the early pilot block).
- **Naming typo resolved**: `ID009/KUK/T1..T5` (acquisition-time typo) is handled transparently as `KOK`; source files are not renamed.
- **Cross-pipeline COM validation**: mean offset between the Theia-inertia-based COM and the Visual3D Dempster-inertia COM across the 180 dynamic trials is 12.1 ± 5.2 mm — within the inter-model differences expected for human inertial parameter sets.
- **Strike-detection plausibility**: hand-speed peak at 4.02 ± 0.21 s (≈ 1 s after the nominal "vai" cue at t = 3 s) with peak speed 5.99 ± 0.74 m/s — consistent with the karate reverse-punch literature.
- **Style-adaptive verbal protocol — quantitative validation**: in the posteriorised base, Shōtōkan trials show a `kōkutsu-dachi`-canonical 92.0 ± 13.7 cm anteroposterior BoS depth vs Gōjū-ryū trials showing a `neko-ashi-dachi`-canonical 53.0 ± 4.4 cm depth — a 39 cm difference and 57 % reduction in BoS area, documenting that the per-trial canonical/stylistic pairing in the metadata is biomechanically load-bearing.

## [0.1.1] — 2026-05-14

### Changed
- `docs/protocol.md`: CEFADE ethics approval number inserted (**CEFADE 09/2025**), replacing the pending-confirmation placeholder.

## [0.1.0] — 2026-05-14

### Added
- Initial repository scaffold.
- `README.md` with dataset overview, stance code table, acquisition protocol summary, citation guidance, and licence note.
- `LICENSE-CODE` (MIT) for code in `src/`.
- `LICENSE-DOCS` (CC-BY 4.0) for `docs/` and README.
- `CITATION.cff` with software and dataset citation metadata.
- Directory scaffold: `src/{matlab,python}`, `data/examples`, `docs`, `figures`.
- Linked to Figshare dataset under reserved DOI [10.6084/m9.figshare.32288943](https://doi.org/10.6084/m9.figshare.32288943).
