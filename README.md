# karate-stances-dataset-scripts

Processing and analysis scripts for the dataset *A Biomechanical Dataset of Fundamental Karate-dō Stances: Markerless Kinematics and Ground Reaction Forces in Twelve Karateka*.

[![DOI](https://img.shields.io/badge/Figshare-10.6084%2Fm9.figshare.32288943-blue)](https://doi.org/10.6084/m9.figshare.32288943)
[![License code](https://img.shields.io/badge/code-MIT-green)](LICENSE-CODE)
[![License docs](https://img.shields.io/badge/docs-CC--BY--4.0-orange)](LICENSE-DOCS)

## Dataset

The dataset is openly available at Figshare under the reserved DOI [10.6084/m9.figshare.32288943](https://doi.org/10.6084/m9.figshare.32288943), CC-BY 4.0 licence.

It contains synchronised force-platform (two Bertec FP4060-15, 1000 Hz) and markerless motion-capture (Qualisys Oqus, 180 Hz; Theia3D reconstruction) recordings of twelve trained karateka executing five 9-second *gyaku-tsuki* trials from each of three fundamental stances:

| Code | Base | Shōtōkan name | Naha-te equivalent |
|---|---|---|---|
| `ZEN` | anteriorised | *zenkutsu-dachi* | *zenkutsu-dachi* |
| `KOK` | posteriorised | *kōkutsu-dachi* | *neko-ashi-dachi* |
| `KIB` | lateralised | *kiba-dachi* | *shiko-dachi* |

Cohort: 4 male + 8 female; 91.7 % black belt; 66.7 % international competitors; 6 Shōtōkan + 5 Gōjū-ryū + 1 Wadō-ryū.

## What this repo contains

This repository holds the *processing and analysis code* that accompanies the dataset (the dataset itself is on Figshare). The split follows Scientific Data conventions: data on a versioned archive (Figshare, DOI), code on a versioned source-control host (GitHub, this repo).

```
karate-stances-dataset-scripts/
├── README.md                  this file
├── LICENSE-CODE               MIT (applies to src/)
├── LICENSE-DOCS               CC-BY 4.0 (applies to docs/ and README)
├── CITATION.cff               machine-readable citation metadata
├── CHANGELOG.md               release log
├── .gitignore
├── src/
│   ├── matlab/                MATLAB processing pipeline (Robalino/Parolini)
│   └── python/                Python helpers for descriptor recomputation
├── data/
│   └── examples/              one example trial per stance (small, for testing scripts)
├── docs/
│   └── protocol.md            acquisition protocol summary
└── figures/                   reproduced figures from the companion paper
```

The Figshare archive at the DOI above carries the full 180-trial dataset, raw and processed signals, per-trial summary descriptors (pre-strike 1–3 s window, post-strike 6–9 s window), and full subject metadata.

## Acquisition protocol

Each participant executed five repetitions of *gyaku-tsuki* from each of the three bases. The full nine-second trial structure is:

```
t = 0 s          —  "atenção" + "gravando" cue, participant assumes the stance
t = 0–3 s        —  pre-strike quasi-static window
t = 3 s          —  "vai" cue, gyaku-tsuki strike executed
t = 3–6 s        —  strike + transient window
t = 6–9 s        —  post-strike re-stabilised quasi-static window
t = 9 s          —  "relaxa" cue, trial closes
```

Verbal instruction of each base was **style-adaptive**: the experimenter named the Shōtōkan-canonical stance and, for participants whose primary style was Naha-te-derived (Gōjū-ryū) or otherwise non-Shōtōkan (Wadō-ryū), the equivalent name in the participant's own tradition (e.g., *neko-ashi-dachi* for the posteriorised base in Gōjū-ryū). The objective was to ensure that each participant executed the configuration that her or his own style identifies with the requested base, rather than imposing a single technical canon.

The full protocol and ethics declaration are in [docs/protocol.md](docs/protocol.md).

## Reproducing the analysis

Scripts are organised by analysis stream. The MATLAB pipeline (`src/matlab/`) reproduces the per-trial descriptors that ship with the Figshare release (`KDS_summary_pre_strike.csv`, `KDS_summary_post_strike.csv`). The Python helpers (`src/python/`) provide convenience loaders, plotting, and aggregate statistics for users who do not have a MATLAB licence.

Both pipelines read the same archive structure: download the Figshare archive, unzip into `data/figshare/`, and the scripts pick up the trial files by their `<ID>_<BASE>_<TRIAL>.csv` naming convention.

A worked example with a single trial per stance is included in `data/examples/` for testing without downloading the full archive.

## Citing

If you use the dataset or these scripts, please cite both:

**Dataset**:
> Pavani, L., Robalino, J. A., Parolini, F., Goethel, M., & Vilas-Boas, J. P. (2026). *A biomechanical dataset of fundamental karate-dō stances: Markerless kinematics and ground reaction forces in twelve karateka* [Data set]. Figshare. https://doi.org/10.6084/m9.figshare.32288943

**Data paper** (in preparation, target *Scientific Data*):
> Pavani, L., Robalino, J. A., Parolini, F., Goethel, M., & Vilas-Boas, J. P. (in preparation). *A biomechanical dataset of fundamental karate-dō stances: Markerless kinematics and ground reaction forces in twelve karateka*.

## Companion empirical paper

The dataset is the empirical substrate of the companion paper introducing the Relative Stability Radius (RSR) descriptor:

> Pavani, L., Robalino, J. A., Goethel, M., & Vilas-Boas, J. P. (in preparation). *Load distribution and vectorial margin of stability in fundamental karate-dō stances: Biomechanical insights into postural control*.

## Authors and contact

- **Luiz Pavani** (corresponding) — up202401900@up.pt — [ORCID 0009-0009-4831-5160](https://orcid.org/0009-0009-4831-5160) — CIFI2D/LABIOMEP, Faculty of Sport, University of Porto
- Johan Andrés Robalino — CIFI2D/LABIOMEP, University of Porto
- Franciele Parolini — CIFI2D/LABIOMEP, University of Porto
- Márcio Goethel — CIFI2D/LABIOMEP, University of Porto (co-supervisor)
- J. Paulo Vilas-Boas — CIFI2D/LABIOMEP, University of Porto (supervisor)

## Acknowledgements

This work was developed within the framework of the first author's master's dissertation in High-Performance Sports Training at the Faculty of Sport, University of Porto. Data acquisition was conducted under the ethics approval granted to the broader doctoral project of J. A. Robalino on fatigue-induced changes in karate attack biomechanics (CEFADE, 2025).

## Licences

- **Code** in `src/`: MIT — see [LICENSE-CODE](LICENSE-CODE)
- **Documentation** and `docs/`: CC-BY 4.0 — see [LICENSE-DOCS](LICENSE-DOCS)
- **Dataset on Figshare**: CC-BY 4.0
