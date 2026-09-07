# Procedure report — kinematic pipeline of the *karate stances* dataset

**Date**: 2026-05-15
**Author**: Luiz Pavani (open Python pipeline)
**Figshare item**: [10.6084/m9.figshare.32288943](https://doi.org/10.6084/m9.figshare.32288943)
**Open code**: <https://github.com/luiz-pavani/karate-stances-dataset-scripts>

This document describes, step by step, how the raw kinematic data exported by Theia3D were transformed into the three analysis tables released alongside the dataset (`kinematic_analysis_wide.csv`, `kinematic_analysis_long.csv`, `kinematic_analysis_codebook.csv`). It is provided for methodological transparency and reviewer reproducibility.

---

## 1. Input data

### 1.1 Raw archive

- **Layout**:
  ```
  Kinematic Data/
  ├── ID003 ... ID014               12 subjects
  │   ├── <ZEN|KOK|KIB>/T<1..5>/    base × trial
  │   │   ├── *_pose_0.c3d          Theia3D raw output
  │   │   ├── *_pose_filt_0.c3d     Theia3D 20 Hz filtered (default for analysis)
  │   │   ├── *_Theia.trc           markers in .trc format
  │   │   ├── Visual3d_SIMM_*.mot   placeholders
  │   └── STATIC/T1/                anatomical reference (ID006-ID014)
  └── Pipelines/                    Visual3D export scripts
  ```
- **Inventory**: 189 trials (180 dynamic + 9 STATIC)
- **Acquisition**: Porto Biomechanics Laboratory (LABIOMEP), 8-camera Qualisys Oqus + 2× Bertec FP4060-15
- **Reconstruction software**: Theia3D v2024.1.24 (markerless)
- **Sampling rate**: 180 Hz
- **Trial duration**: 9.00 s exactly (1620 frames)

### 1.2 Pre-processing audit

Before writing any production code we ran a complete inventory:

```bash
find "<archive>" -type f | sed 's/.*\.//' | sort | uniq -c
#   573 c3d
#   180 txt   (Visual3D POS+COM exports)
#     4 v3s   (Visual3D scripts)
#     2 mot   (SIMM placeholders)
#     1 trc, 1 cmz, 1 cmx
```

**Anomalies detected and handled**:

1. **Acquisition-time typo**: folder `ID009/KUK/` should have read `KOK` — operator typo. Resolved in the loader (`BASE_CANONICAL = {"KUK": "KOK"}`) without renaming source files (source preservation).
2. **Missing STATIC** for ID003, ID004, ID005 — pilot session without anatomical reference; treated by normalising on the first second of the trial.
3. **`ALL_TRIALS` and `ALL_TRIALS_BASES` folders** with copies of `_pose_filt_0.c3d` — ignored in `discover_trials()` to avoid duplication.

### 1.3 C3D inspection

Each C3D verified via `ezc3d` contains:
- `data.rotations`: shape `(4, 4, 19, 1620)` — 19 segments × 4×4 matrix × 1620 frames
- `data.points`: empty (no traditional markers — Theia is markerless)
- `data.analogs`: empty (kinetics in a separate file)
- **THEIA3D parameters**: sex-specific inertia per segment (mass percentage, COM in segment frame, radii of gyration)

The 19 segments:
```
worldbody, pelvis, l_thigh, l_shank, l_foot, l_toes,
r_thigh, r_shank, r_foot, r_toes,
head, torso,
l_uarm, l_larm, l_hand, r_uarm, r_larm, r_hand,
pelvis_shifted
```

---

## 2. Computational environment

### 2.1 Stack

| Component | Version | Rationale |
|---|---|---|
| **Python** | 3.13.2 | open-source; replicable by any reviewer without MATLAB licence |
| **ezc3d** | 1.7.0 | official C3D reader (Wagnon Sangeux/Inria); equivalence with MATLAB BTK |
| **numpy** | 2.4.1 | linear algebra |
| **scipy** | 1.17.1 | Butterworth filter and `Rotation` for Euler decomposition |
| **pandas** | 3.0.0 | DataFrame and CSV I/O |
| **matplotlib** | 3.10.9 | diagnostic figures |

### 2.2 Input decision

We use **`_pose_filt_0.c3d`** as the default input (Theia has already applied a zero-lag 20 Hz Butterworth filter, validated in Kanko et al. 2021a,b). The raw `_pose_0.c3d` files are also released so that users can re-filter with their own parameters.

---

## 3. Pipeline architecture

The pipeline is organised in 8 modules with isolated responsibilities, under `karate-stances-dataset-scripts/src/python/kds/`:

```
kds/
├── loader.py             ─ C3D + Visual3D POS reader; KUK→KOK alias; trial discovery
├── demographics.py       ─ canonical 12-subject table
├── kinematics_linear.py  ─ joint centres + whole-body COM + velocities + accelerations
├── kinematics_angular.py ─ 12 ISB joint angles
├── strike_detection.py   ─ automatic gyaku-tsuki detection from hand speed
├── descriptors.py        ─ per-window descriptor panel
├── batch.py              ─ CLI driver across the 189 trials
└── plots.py              ─ diagnostic figures
```

---

## 4. Processing — step by step

### Step 1 — Loader (`loader.py`)

**Input**: path to a C3D file.
**Output**: `TrialRecord` dataclass containing `subject`, `base`, `trial`, `filtered`, `rate_hz`, `n_frames`, `time` (time array), `segments` (`{label: (4, 4, n_frames)}` — 19 transforms over time), `inertia` (sex-specific inertial parameters per segment), and `metadata` (Theia version, model, filters, paths).

**Validation**: filename regex validates nomenclature; `BASE_CANONICAL = {"KUK": "KOK"}` resolves the typo silently; `rate_hz=180.0` and `n_frames=1620` cross-checked in every dynamic trial.

### Step 2 — Linear kinematics (`kinematics_linear.py`)

**2.1 Joint centres (segment origin position)**

For each segment, the origin position in the laboratory frame is the column 4 (translation) of the 4×4 homogeneous matrix:
```
T_segment = [ R  t ]   →  position_lab = T[0:3, 3, :]
            [ 0  1 ]
```

**2.2 Whole-body centre of mass**

Formula:
```
COM_lab(t) = Σ_i m_i × (R_i(t) × COM_local_i + t_i(t))  /  Σ_i m_i
```
where `m_i` is the mass fraction of segment `i` (Theia-stored, sex-specific); `COM_local_i` is the COM position in the segment frame (Theia-stored); `R_i(t), t_i(t)` are the rotation and translation of the segment in the laboratory frame at time `t`. Implemented in `whole_body_com()` via vectorised einsum, using sex-specific parameters from the demographic table.

`pelvis` and `pelvis_shifted` have no inertial parameters in the Theia model (the lower-trunk mass is redistributed between thorax and thighs) — they are excluded from the summation.

**2.3 Velocities and accelerations**

- Velocity: `np.gradient(position, 1/rate, axis=-1)` (central differences)
- Acceleration: pre-filtering with a 4th-order zero-lag 6 Hz Butterworth + double differentiation (suppresses noise amplified by the second derivative)

### Step 3 — Angular kinematics (`kinematics_angular.py`)

**3.1 Joint definitions (12 joints × 3 axes = 36 DoF)**

Following ISB recommendations (Wu et al. 2002 for lower limb and spine; Wu et al. 2005 for upper limb):

| Joint | Parent | Child | Euler sequence |
|---|---|---|---|
| hip_right/left | pelvis | thigh | Z-X-Y |
| knee_right/left | thigh | shank | Z-X-Y |
| ankle_right/left | shank | foot | Z-X-Y |
| shoulder_right/left | torso | uarm | Y-X-Z |
| elbow_right/left | uarm | larm | Y-X-Z |
| pelvis_world | worldbody | pelvis | Z-X-Y |
| trunk | pelvis | torso | Z-X-Y |

**3.2 Decomposition**

```python
R_rel = R_parent.T @ R_child
angles = Rotation.from_matrix(R_rel).as_euler(seq, degrees=True)
```

The three angles correspond to flexion/extension (axis 0), abduction/adduction (axis 1), and internal/external rotation (axis 2).

**3.3 ROM**

For each window (pre-strike or post-strike), `ROM = max − min` per axis. Dynamic elbow ROM can hit gimbal lock (ROM 360°) — a known Euler limitation; static pre/post windows are not affected.

### Step 4 — Strike detection (`strike_detection.py`)

**Algorithm**:
1. Compute scalar (magnitude) velocity of `r_hand` and `l_hand` origins.
2. Automatically select the side with the higher peak speed.
3. Mark `peak_time` (time of the maximum), `peak_speed` (magnitude at the peak), `onset_time` (first ascending crossing of 10 % of peak before the peak), and `return_time` (first descending crossing of 10 % of peak after the peak).

**Descriptive validation (180 trials)**:
- Peak time: 4.02 ± 0.21 s (≈ 1 s after the nominal "*vai*" at 3 s — consistent with reaction + execution)
- Peak speed: 5.99 ± 0.74 m·s⁻¹ (in the 5–9 m·s⁻¹ range reported for elite and sub-elite *tsuki*)

### Step 5 — Descriptors (`descriptors.py`)

**Analysis windows**:
- `pre_strike = [1.0, 3.0] s` → 360 frames (assumed posture, before "vai")
- `post_strike = [6.0, 9.0] s` → 540 frames (re-stabilised posture after the strike)
- Strike window `[3.0, 6.0] s` preserved in the time-series but excluded from summary descriptors

**Per-window descriptor panel (50+ scalars)**:

*Anatomical axis mapping (stance-dependent)*: `ZEN`/`KOK` face lab +Y (X = ML, Y = AP); `KIB` faces lab +X (X = AP, Y = ML) — verified against the gyaku-tsuki punch direction in all 180 dynamic trials. All `_ml_`/`_ap_` descriptors below apply this per-stance mapping (pipeline ≥ v0.5.0; earlier releases mislabelled the `KIB` pairs — pure label permutation, values unchanged).

*COM (9 columns per window)*: `com_x/y/z_mean_m`; `com_ml/ap/z_range_cm`; `com_ml/ap_rms_cm`; `com_path_length_cm` (2D ML+AP).

*Joint angles (24 columns per window = 12 joints × 2 statistics)*: `<joint>_<flx|abd|rot>_mean_deg`; `<joint>_<flx|abd|rot>_rom_deg`.

*BoS (5 columns, pre-strike only — the feet are fixed)*: `bos_width_ml_cm`; `bos_depth_ap_cm`; `bos_area_cm2` (bounding box of the 6 foot landmarks); `bos_centroid_x/y`.

*Strike event (5 columns)*: `strike_hand`, `strike_peak_speed_mps`, `strike_peak_time_s`, `strike_onset_time_s`, `strike_return_time_s`.

*Cross-pipeline validation (1 column)*: `v3d_com_offset_norm_mm` — mean distance between the Theia-inertia COM and the Dempster-inertia COM exported by Visual3D. Expected range: ~10–20 mm (model-difference offset).

### Step 6 — Batch driver (`batch.py`)

**Command**:
```bash
python -m kds.batch \
  --data-root <path to Kinematic Data> \
  --output-dir ./output
```

**Procedure**:
1. `discover_trials()` returns 189 paths (180 dynamic + 9 STATIC).
2. `discover_pos_txt()` maps the 180 Visual3D POS exports.
3. For each trial: (a) `read_c3d_trial()` loads; (b) STATIC trials → COM mean across the full duration; (c) dynamic trials → `trial_descriptors()` computes the full panel.
4. Emits five outputs:
   - `summary_all_trials.csv` (180 rows × 181 columns)
   - `summary_static.csv` (9 rows × 12 columns)
   - `subject_means.csv` (36 rows — per-subject × base means)
   - `qc_report.csv` (189 rows — QC flags)
   - `pipeline_metadata.json` (pipeline version + timestamp)

**Runtime**: ~70 seconds for the 189 trials on a laptop. **Result**: 189/189 trials processed without error.

### Step 7 — Analysis consolidation (`build_analysis_csv.py`)

From `summary_all_trials.csv`, the final step joins demographics and produces the three analysis CSVs:

**7.1 Wide format (`kinematic_analysis_wide.csv`, 180 × ~200)**: columns reordered (identifiers → demographics → descriptors); five height-normalised variables added for cross-subject comparison: `com_height_norm_by_height = pre_com_z_mean_m / (height_cm/100)`; `bos_area_norm_by_height_sq_pct = bos_area_cm² / height_cm² × 100`; `bos_width_norm_by_height_pct`; `bos_depth_norm_by_height_pct`; `strike_peak_speed_norm_by_height_sqrt`.

**7.2 Long format (`kinematic_analysis_long.csv`, 31 860 × 22)**: melt of the wide CSV — one row per (trial, metric); each row carries `id_vars` (subject, base, sex, style, etc.) + (`metric`, `value`); auto-annotation parses each metric name into `window`, `family`, `joint`, `axis`, `stat`, and `unit`; ready for `lmer()` in R or `mixedlm()` in statsmodels.

**7.3 Codebook (`kinematic_analysis_codebook.csv`, 200 × 3)**: one row per column of the wide CSV; fields `column`, `description`, `dtype`; descriptions built via a lookup table for identifiers and demographics and prefix-family heuristics (`pre_com_`, `post_hip_`, etc.).

---

## 5. Validation and QC

### 5.1 Trial completeness
180/180 dynamic trials processed; 9/9 STATIC processed; 0 errors.

### 5.2 Cross-pipeline validation
COM computed by the pipeline (Theia sex-specific inertia) versus the COM exported by Visual3D (Dempster inertia): **mean offset 13.5 ± 4.2 mm** across the 180 trials. The literature-expected magnitude between distinct inertial models is 10–20 mm.

### 5.3 Strike-detection plausibility
Peak time 4.02 ± 0.21 s vs nominal "*vai*" at 3.00 s — a reaction-plus-execution latency near 1 s, in line with reported *tsuki* reaction times (Pozo 2011; Cesari 2008).

### 5.4 Biomechanical sanity check

`BoS depth (cm) × base × style`:
```
style       Goju-Ryu  Shotokan
base                          (n=25)    (n=35)
KIB           102.1      94.7
KOK            53.0      90.3   ← within-base stylistic contrast
ZEN            88.6      84.3
```

KOK Gōjū-ryū 53 cm vs Shōtōkan 90 cm = a 37 cm difference (58 % reduction in area), confirming that Gōjū-ryū practitioners execute *neko-ashi-dachi* even when verbally instructed under the Shōtōkan canonical name *kōkutsu-dachi*. Quantitative validation of the style-adaptive protocol.

`COM height (m) × base × style`:
```
style       Goju-Ryu  Shotokan
base                          (n=25)    (n=35)
KIB           0.601     0.717   ← within-base stylistic contrast
KOK           0.710     0.745
ZEN           0.682     0.738
```

KIB Gōjū-ryū 0.60 m vs Shōtōkan 0.72 m = a 12 cm difference, consistent with *shiko-dachi* (Naha-te lateralised stance, 45° foot rotation, internally-rotated femurs, lower COM) versus *kiba-dachi* (Shōtōkan).

---

## 6. Methodological decisions and rationale

| Decision | Alternative | Rationale |
|---|---|---|
| Python as language | MATLAB | open-source; no licence required; reproducible by any reviewer |
| Input: `_pose_filt_0.c3d` | `_pose_0.c3d` (raw) | Theia native 20 Hz is validated (Kanko 2021a,b); raw also released for freedom |
| Inertia: Theia sex-specific | Dempster generic | Theia parameters are model-specific; Visual3D Dempster used for the cross-check |
| Strike auto-detection (10 % peak) | Manual threshold | Robust to inter-subject variation; consistent across trials |
| Windows [1, 3] s and [6, 9] s | [0, 3] s and [6, 9] s | Excluding the first second removes posture-assumption transients |
| ISB Wu 2002/2005 | Alternative systems | De facto standard in clinical and sport biomechanics |
| KUK→KOK in loader | Rename source files | Preserves source provenance; correction is transparent |

---

## 7. Known limitations

1. **STATIC missing for ID003–ID005** — first pilot session without reference. Treated via normalisation on the first second of each trial.
2. **Dynamic elbow ROM** can hit gimbal lock during wide movements (Euler degeneracy); static pre/post windows are not affected.
3. **Pelvis and `pelvis_shifted` carry no inertia** in the Theia model — that mass is redistributed across thorax and thighs in Theia's parameterisation. The model-difference relative to Dempster amounts to the 13.5 mm cross-pipeline offset observed.
4. **Wadō-ryū and Shitō-ryū absent** — cohort covers only two lineages (Shōtōkan n = 7; Gōjū-ryū n = 5).
5. **Kinetic-stream integration** — the force-platform stream is released alongside as a raw archive at 1000 Hz; derived metrics (combined COP, COP–COM coupling, margin of stability, RSR) are explicitly user-side computations.

---

## 8. Reproducibility

To regenerate the three analysis CSVs:

```bash
# 1. Clone repository
git clone https://github.com/luiz-pavani/karate-stances-dataset-scripts
cd karate-stances-dataset-scripts

# 2. Install dependencies
pip install -e .

# 3. Run pipeline (writes the five outputs under ./output)
python -m kds.batch \
  --data-root <path to Kinematic Data> \
  --output-dir ./output

# 4. Consolidate to analysis tables (writes three CSVs under data/processed_summary/)
python src/python/build_analysis_csv.py
```

Pipeline version used to produce this release: **v0.4.0**.

---

*Document derived from the real pipeline execution against the released dataset. Code: <https://github.com/luiz-pavani/karate-stances-dataset-scripts>. Data: <https://doi.org/10.6084/m9.figshare.32288943>.*
