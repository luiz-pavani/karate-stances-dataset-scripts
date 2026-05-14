# Changelog

All notable changes to this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- MATLAB processing pipeline (`src/matlab/`): synchronisation, low-pass filter, COP/COM/BoS descriptor computation, pre-strike and post-strike window extraction.
- Python helpers (`src/python/`): trial-file loader, descriptor recomputation, plotting utilities.
- Worked-example data in `data/examples/` (one trial per stance).

## [0.1.0] — 2026-05-14

### Added
- Initial repository scaffold.
- `README.md` with dataset overview, stance code table, acquisition protocol summary, citation guidance, and licence note.
- `LICENSE-CODE` (MIT) for code in `src/`.
- `LICENSE-DOCS` (CC-BY 4.0) for `docs/` and README.
- `CITATION.cff` with software and dataset citation metadata.
- Directory scaffold: `src/{matlab,python}`, `data/examples`, `docs`, `figures`.
- Linked to Figshare dataset under reserved DOI [10.6084/m9.figshare.32288943](https://doi.org/10.6084/m9.figshare.32288943).
