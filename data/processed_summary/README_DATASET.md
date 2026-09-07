# Karate Stances Dataset — README

**Dataset DOI**: [10.6084/m9.figshare.32288943](https://doi.org/10.6084/m9.figshare.32288943)
**License**: Creative Commons Attribution 4.0 International (CC-BY 4.0)
**Code repository**: <https://github.com/luiz-pavani/karate-stances-dataset-scripts> (MIT)
**Companion paper**: Pavani, L., Robalino, J. A., Parolini, F., Goethel, M., & Vilas-Boas, J. P. *A Biomechanical Dataset of Fundamental Karate-dō Stances: Markerless Kinematics and Ground Reaction Forces in Twelve Karateka*. Submitted to *Scientific Data* (2026).
**Contact (corresponding author)**: Luiz Pavani — `up202401900@up.pt` — ORCID 0009-0009-4831-5160

---

## 1. Overview

Synchronised markerless three-dimensional kinematic and dual-force-platform kinetic recordings of twelve trained karateka (4 male + 8 female; 11 black belt, 1 white belt; 7 Shōtōkan, 5 Gōjū-ryū) executing five 9-second *gyaku-tsuki* repetitions from each of three fundamental karate stances:

| Code | Base | Shōtōkan canonical name | Naha-te (Gōjū-ryū) equivalent |
|---|---|---|---|
| `ZEN` | anteriorised | *zenkutsu-dachi* | *zenkutsu-dachi* |
| `KOK` | posteriorised | *kōkutsu-dachi* | *neko-ashi-dachi* |
| `KIB` | lateralised | *kiba-dachi* | *shiko-dachi* |

Acquisition was conducted in the Porto Biomechanics Laboratory (LABIOMEP) using 8 Qualisys Oqus cameras (180 Hz, markerless Theia3D v2024.1.24 reconstruction, 19-segment biomechanical model) and two Bertec FP4060-15 force platforms (1000 Hz, lab-frame). 192 trials are released (180 dynamic + 12 STATIC reference; 9 of the 12 STATIC trials have both a kinematic and a kinetic record, 3 have a kinetic record only).

### Coordinate frame and anatomical axes

All time-series are expressed in the laboratory frame (X, Y horizontal; Z vertical, upward positive). **The anatomical meaning of the two horizontal axes is stance-dependent**, because the stances were not all performed facing the same laboratory direction (verified against the gyaku-tsuki punch direction in all 180 dynamic trials): `ZEN` and `KOK` trials face lab +Y (X = mediolateral, Y = anteroposterior); `KIB` trials face lab +X (X = anteroposterior, Y = mediolateral). The `_ml_`/`_ap_` descriptors in the derived analysis tables already apply this per-stance mapping. *Correction note:* releases of the derived tables prior to v0.5.0 of the companion pipeline applied X = mediolateral to all stances, which mislabelled (not mis-measured) the ML/AP descriptor pairs of the `KIB` rows; the values were unchanged and only the labels were permuted (see the repository `CHANGELOG.md`).

## 2. Files released on Figshare

| File | Size | Content |
|---|---|---|
| `KDS_kinematic_raw_c3d.zip` | 812 MB | Raw and Theia-filtered C3D output (`*_pose_0.c3d`, `*_pose_filt_0.c3d`) for the 19-segment Theia3D reconstruction, organised as `<subject>/<base>/T<n>/`. Native Theia3D format. |
| `KDS_kinematic_timeseries.zip` | 103 MB | Per-trial kinematic CSVs at 180 Hz, 98 columns each (1620 frames per dynamic trial). 180 dynamic + 9 STATIC files. |
| `KDS_kinetic_raw_tsv.zip` | 110 MB | Raw force-platform TSV files exported by Qualisys QTM from both Bertec platforms (FP3 + FP4), 1000 Hz, two header variants (11-col for ID003–ID004; 9-col for ID005–ID014). |
| `KDS_kinetic_timeseries.zip` | 122 MB | Per-trial kinetic CSVs at 1000 Hz, 20 columns each (9000 frames per dynamic trial; variable for STATIC). 180 dynamic + 12 STATIC + the QC report + the lab-frame plate-corner table. |
| `KDS_kinematic_analysis.zip` | 0.8 MB | Three derived analysis tables — wide format, long format, and codebook — emitted by the open pipeline; full pipeline procedure report in English. Provided as a reproducible analytic example; re-users are encouraged to regenerate from the time-series with the pipeline of their choice. |
| `KDS_Info.xlsx` | ≤ 0.1 MB | Per-trial metadata workbook (192 rows × 23 columns) with the per-trial subject identifier, base code, canonical-Shōtōkan and stylistic-executed name pairing, subject demographics, training history, competition modality and level, and limb-dominance. |
| `README.md` | this file | Top-level documentation. |

## 3. Trial nomenclature

Trial IDs follow `<subject>_<base>_T<repetition>`. Example: `ID003_ZEN_T1` = participant `ID003`, anteriorised base, repetition 1. The `KUK→KOK` typo in the acquisition-time folder structure of `ID009` was resolved during export; released filenames consistently use `KOK`.

## 4. Style-adaptive verbal protocol

A single experimenter issued the verbal command at the third second of each trial using the canonical Shōtōkan name of the base (e.g., *kōkutsu-dachi* for the posteriorised base). Gōjū-ryū participants executed the Naha-te equivalent (*neko-ashi-dachi* for the same posteriorised base; *shiko-dachi* for the lateralised base). The pairing canonical-name ↔ executed-name is recorded per trial in `KDS_Info.xlsx`. This design lets re-users probe within-base biomechanical contrast across style lineages (e.g., 37 cm difference in base-of-support depth between *kōkutsu-dachi*, 90.3 cm, and *neko-ashi-dachi*, 53.0 cm) without confounding from across-protocol comparison.

## 5. Schema details

### 5.1 Kinematic per-trial CSV (`KDS_kinematic_timeseries/*_kinematics.csv`)

98 columns: 2 identifying (`frame`, `time_s`) + 57 segment origins (19 segments × 3 axes: `<seg>_x`, `<seg>_y`, `<seg>_z` in metres, lab frame) + 3 whole-body centre-of-mass (`com_x`, `com_y`, `com_z`, metres, sex-specific de Leva inertial parameters) + 36 joint angles (12 ISB joints × 3 axes Cardan/Euler in degrees, Wu 2002/2005 conventions: `<joint>_flx_deg`, `<joint>_abd_deg`, `<joint>_rot_deg`).

Segments: `worldbody`, `pelvis`, `l_thigh`, `l_shank`, `l_foot`, `l_toes`, `r_thigh`, `r_shank`, `r_foot`, `r_toes`, `head`, `torso`, `l_uarm`, `l_larm`, `l_hand`, `r_uarm`, `r_larm`, `r_hand`, `pelvis_shifted`.

Joints: `hip_right`, `hip_left`, `knee_right`, `knee_left`, `ankle_right`, `ankle_left`, `shoulder_right`, `shoulder_left`, `elbow_right`, `elbow_left`, `pelvis_world`, `trunk`.

### 5.2 Kinetic per-trial CSV (`KDS_kinetic_timeseries/*_kinetics.csv`)

20 columns: 2 identifying (`frame`, `time_s`) + 9 per Bertec platform (`FP3_*` and `FP4_*`): forces `Fx`, `Fy`, `Fz` (N); free moments `Mx`, `My`, `Mz` (N·mm) about each plate centre; centre-of-pressure `COPx`, `COPy`, `COPz` (mm) in the laboratory frame. Bertec sign convention: a participant standing on a plate produces a negative `Fz`. Absent-plate columns (5 single-platform trials) are filled with `NaN`s; the QC report flags these per trial.

### 5.3 Auxiliary kinetic tables (within `KDS_kinetic_timeseries.zip`)

- `kinetic_qc_report.csv` (192 rows × 12 cols): per-trial completeness flags, which platforms fired, sample count, header-variant, lab-frame origin offset.
- `kinetic_plate_corners.csv` (1 516 rows × 7 cols): the four lab-frame corner coordinates of each plate per trial, written by Qualisys QTM at acquisition time.

### 5.4 Analytic tables (`KDS_kinematic_analysis.zip`)

- `kinematic_analysis_wide.csv`: 180 rows × ~110 columns; one row per dynamic trial; pre-strike (1–3 s) and post-strike (6–9 s) window means and ROMs for the 12 joints × 3 axes, base-of-support width/depth/area/centroid, whole-body COM mean position and sway descriptors, detected strike-event timing and peak hand-speed.
- `kinematic_analysis_long.csv`: same content reshaped to a tidy long format (one row per trial × variable × window).
- `kinematic_analysis_codebook.csv`: variable-level codebook with units, computation rule, and window definition.
- `PROCEDURE_REPORT.md`: full English-language methodological narrative of how the analytic tables are derived from the raw C3D — provided for transparency; the same procedure is executable from the open pipeline (see §7).

These analytic tables are released as a reproducible reference computation, not as the canonical analytical artefact. Re-users with different processing choices (different filtering, different windowing, derived kinetic descriptors, alternative COP-based metrics) should regenerate analogous tables from the per-trial time-series streams.

## 6. What the dataset deliberately does **not** contain

The release follows a minimal-processing design. The following classes of artefact are **not** distributed and are the responsibility of the re-user:

- Inferential statistics (group-level *t*-tests, ANOVAs, regression models).
- Additional filtering beyond the Theia3D native 20 Hz output and the raw C3D (which is released alongside the filtered C3D so re-users can apply their own filter).
- Derived kinetic descriptors that depend on a choice of platform combination rule — force-weighted combined centre of pressure, COP–COM coupling, dynamic margin of stability, the Relative Stability Radius introduced in the companion empirical paper (Pavani et al., submitted), etc.
- Decision on what to do with the five single-platform-only trials: they are retained with `NaN`s and the decision is left to the re-user.
- Personally identifiable information of any kind: participants are referred to exclusively by anonymised session identifiers `ID003` through `ID014`.

## 7. Open pipeline (regenerating the analytic tables)

The pipeline that produced the analytic tables in `KDS_kinematic_analysis.zip` is open source: [github.com/luiz-pavani/karate-stances-dataset-scripts](https://github.com/luiz-pavani/karate-stances-dataset-scripts) (MIT licence). Installation:

```bash
git clone https://github.com/luiz-pavani/karate-stances-dataset-scripts.git
cd karate-stances-dataset-scripts
pip install -e .
```

Minimal reproducible example to load a single trial and recompute the whole-body centre of mass:

```python
from kds.loader import read_c3d_trial
from kds.kinematics_linear import whole_body_com
from kds.demographics import SUBJECTS

trial_path = "KDS_kinematic_raw_c3d/ID003/ZEN/T1/ID003_ZEN_T1_pose_filt_0.c3d"
rec = read_c3d_trial(trial_path)
com = whole_body_com(rec, sex=SUBJECTS[rec.subject].sex)   # (3, n_frames) ndarray
print(com[:, 0])   # COM at frame 0, lab-frame, metres
```

Full pipeline regeneration (recomputes every analytic table from the raw archive):

```bash
python -m kds.batch --data-root /path/to/KDS_kinematic_raw_c3d --output-dir ./out
```

## 8. Data citation

Pavani, L., Robalino, J. A., Parolini, F., Goethel, M., & Vilas-Boas, J. P. (2026). *Karate Stances Dataset*. Figshare. <https://doi.org/10.6084/m9.figshare.32288943>

## 9. Acknowledgements and ethics

All participants were recruited in the Porto metropolitan karate community, provided written informed consent in accordance with the Declaration of Helsinki, and were free to withdraw at any time. The data acquisition was conducted under the ethics approval `CEFADE 09/2025` of the Faculty of Sport, University of Porto. The dataset was released within the framework of the first author's master's dissertation in High-Performance Sports Training (FADEUP) and is offered under CC-BY 4.0; the code that processes it is released under MIT.

---

*README v1.0 — 2026-05-18 (data records frozen at Figshare 32288943).*
