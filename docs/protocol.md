# Acquisition protocol

This document summarises the protocol used to acquire the dataset. The authoritative protocol description is in §2.3 of the companion data paper (in preparation, target *Scientific Data*).

## Cohort

- N = 12 trained karateka (four male, eight female)
- 91.7 % black belt (≥ 1 Dan; 11/12 — two 3rd Dan, nine 1st Dan); one white-belt entry-level practitioner retained to characterise the lower bound of the experience continuum
- 66.7 % international competitors; two national; one regional
- 6 competing primarily in *kata* + 5 in *kumite*
- Style stratification: 6 Shōtōkan + 5 Gōjū-ryū + 1 Wadō-ryū (descriptive single-subject reference)
- Mean age 23.8 ± 7.5 years (range 19–45)
- Mean stature 163.3 ± 8.1 cm
- Mean body mass 72.2 ± 14.9 kg
- BMI 26.96 ± 4.60 kg·m⁻²
- Mean training history 13.8 ± 5.5 years (range 1–25)

## Equipment

- **Force platforms**: two Bertec FP4060-15, 1000 Hz, flush with floor.
- **Motion capture**: eight-camera Qualisys Oqus system, 180 Hz.
- **Markerless reconstruction**: Theia3D software (Theia Markerless Inc., Kingston, Ontario, Canada). Concurrent validity assessed by Kanko et al. (2021a, 2021b).
- **Synchronisation**: hardware trigger between kinematic and kinetic streams.
- **Analysis**: MATLAB custom scripts.

## Trial structure

Each participant performed five repetitions of *gyaku-tsuki* from each of the three bases, in randomised order recorded on the evaluation sheet. Total: 15 trials × 12 participants = 180 trials (plus 12 static-reference recordings).

```
t = 0 s    "atenção" + "gravando"   participant assumes the stance
t = 0–3 s  pre-strike window         quasi-static hold
t = 3 s    "vai"                     gyaku-tsuki strike executed
t = 3–6 s  strike + transient
t = 6–9 s  post-strike window        re-stabilised quasi-static hold
t = 9 s    "relaxa"                  trial closes
```

## Style-adaptive verbal instruction

Verbal instruction was paired between the Shōtōkan-canonical name and the participant's stylistic equivalent. The pairing convention:

| Base mechanic | Shōtōkan cue | Naha-te equivalent | Wadō-ryū equivalent |
|---|---|---|---|
| anteriorised | *zenkutsu-dachi* | *zenkutsu-dachi* | *zenkutsu-dachi* |
| posteriorised | *kōkutsu-dachi* | *neko-ashi-dachi* | *neko-ashi-dachi* / *kōkutsu-dachi* |
| lateralised | *kiba-dachi* | *shiko-dachi* | *kiba-dachi* |

The objective was to ensure that each participant executed the configuration that her or his own style identifies with the requested base, rather than imposing a single technical canon. The per-trial pairing of canonical and stylistic-equivalent names is recorded explicitly in the dataset metadata.

## File naming convention

```
<ID>_<BASE>_<TRIAL>.csv      e.g., ID003_ZEN_T1.csv
<ID>_STATIC.csv              anatomical reference (2 s on FP3)
```

- `<ID>`: `ID003`–`ID014` (twelve participants; `ID001`–`ID002` are pilot sessions, not released).
- `<BASE>`: `ZEN` (anteriorised), `KOK` (posteriorised), `KIB` (lateralised).
- `<TRIAL>`: `T1`–`T5`.

## Foot placement

- Front foot on FP3, rear foot on FP4 (LABIOMEP installation numbering).
- For `KIB` (symmetric base), FP3/FP4 assignment is arbitrary and treated as left/right.
- Inter-foot distance: each participant's preferred technical distance.
- Foot orientation: by the stance convention of the participant's own style.

## Analysis windows

Two windows are extracted per trial:

- **Pre-strike** — seconds 1–3 (2 s), characterising the unloaded quasi-static stance.
- **Post-strike** — seconds 6–9 (3 s), characterising the re-stabilised stance after the *gyaku-tsuki* transient has settled.

The strike window (seconds 3–6) is preserved in the released time-series data but excluded from the summary postural descriptors.

## Ethics

Approved under the parent CEFADE protocol (Robalino doctoral project on fatigue-induced changes in karate attack biomechanics, submitted 21 March 2025; approval number pending administrative confirmation). All participants provided written informed consent prior to data collection in accordance with the Declaration of Helsinki. Data handling complies with the General Data Protection Regulation (EU 2016/679).

## References

- Kanko, R. M., Laende, E. K., Davis, E. M., Selbie, W. S., & Deluzio, K. J. (2021). Concurrent assessment of gait kinematics using marker-based and markerless motion capture. *Journal of Biomechanics*, 127, 110665. <https://doi.org/10.1016/j.jbiomech.2021.110665>
- Kanko, R. M., Laende, E. K., Selbie, W. S., & Deluzio, K. J. (2021). Inter-session repeatability of markerless motion capture gait kinematics. *Journal of Biomechanics*, 121, 110422. <https://doi.org/10.1016/j.jbiomech.2021.110422>
