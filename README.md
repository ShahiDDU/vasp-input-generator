# VASP Input Generator

A web-based GUI for generating [VASP](https://www.vasp.at/) input files — **INCAR**, **POSCAR**, **KPOINTS**, and **POTCAR** — through a clean, step-by-step wizard. No coding required.

Built with [Streamlit](https://streamlit.io) and deployable anywhere with a browser.

---

## Features

- **6-step wizard** — guided workflow from structure to ready-to-run input files
- **Crystal structure** — upload POSCAR or CIF, choose from presets, or paste manually
- **INCAR generator** — 10+ calculation types with smart defaults and contextual tips:
  - SCF, Ionic Relaxation, Full Relaxation (vc-relax)
  - Band Structure, DOS
  - HSE06 hybrid functional
  - DFT+U (Hubbard U)
  - Spin-Orbit Coupling (SOC)
  - Molecular Dynamics (NVT)
  - meta-GGA (mBJ, R2SCAN)
- **KPOINTS** — Gamma-centered, Monkhorst-Pack, Gamma-only, line-mode band paths
- **POTCAR guide** — recommended pseudopotential variants for every element (PBE / LDA)
- **Download** — individual files or all-in-one ZIP
- **Run VASP locally** — launch `vasp_std`, `vasp_gam`, or `vasp_ncl` directly from the UI with live output monitoring
- **Results viewer** — parse OUTCAR, plot SCF convergence, display forces and Fermi energy

---

## Screenshots

| Step 1 — Structure | Step 2 — INCAR | Step 5 — Download |
|---|---|---|
| Upload CIF / POSCAR | All parameters with tips | Preview + ZIP download |

---

## Quick Start (local)

```bash
git clone https://github.com/ShahiDDU/vasp-input-generator.git
cd vasp-input-generator
pip install -r requirements.txt
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Deploy on Streamlit Community Cloud (free)

1. Fork this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) → **Create app**
3. Select your fork, branch `main`, file `app.py`
4. Click **Deploy**

> **Note:** The POTCAR assembly and Run VASP steps require a local VASP installation and are automatically hidden in the cloud version. All input file generation (INCAR, POSCAR, KPOINTS) works fully in the cloud.

---

## Calculation Types

| Type | Description |
|------|-------------|
| `scf` | Self-consistent field — ground-state energy and charge density |
| `relax` | Ionic relaxation — optimise atom positions at fixed cell |
| `vc-relax` | Variable-cell relaxation — optimise both positions and cell |
| `bands` | Band structure along a high-symmetry k-path |
| `dos` | Density of states on a dense k-mesh |
| `hse06` | Hybrid functional (HSE06 / PBE0) |
| `dftu` | DFT+U for correlated d/f systems |
| `soc` | Non-collinear + spin-orbit coupling |
| `md_nvt` | Born-Oppenheimer NVT molecular dynamics |
| `mbj` | Modified Becke-Johnson meta-GGA band gap |
| `r2scan` | r²SCAN meta-GGA functional |

---

## POTCAR Note

POTCAR files are **proprietary to VASP** and cannot be distributed. The cloud version shows which pseudopotential variant to use for each element. To assemble POTCAR locally:

```bash
cat $VASP_PSP_DIR/PBE/{Fe_pv,O}/POTCAR > POTCAR
```

---

## Updating

Every `git push` to `main` automatically redeploys on Streamlit Cloud.

```bash
# make your changes
git add -A
git commit -m "v1.x: describe what changed"
git push
```

---

## Requirements

| Package | Purpose |
|---------|---------|
| `streamlit` | Web UI framework |
| `pymatgen` | CIF parsing and structure handling |
| `numpy` | Numerical operations |
| `matplotlib` | SCF convergence plots |

---

## Project Structure

```
vasp-input-generator/
├── app.py                  # Main Streamlit application
├── core/
│   ├── incar_data.py       # INCAR parameter definitions and templates
│   ├── poscar.py           # POSCAR parsing and CIF conversion
│   ├── kpoints.py          # K-point generation utilities
│   ├── potcar.py           # POTCAR assembly (local only)
│   └── runner.py           # VASP job runner and output parser
├── requirements.txt
└── .streamlit/
    └── config.toml         # Theme and server settings
```

---

## License

This project is open-source. VASP itself requires a separate commercial license from [vasp.at](https://www.vasp.at).
