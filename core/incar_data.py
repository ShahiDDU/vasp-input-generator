"""INCAR parameter definitions and calculation templates."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────────────────────────────────────
# PARAM_INFO  –  metadata for every supported INCAR tag
#   type    : int | float | str | bool
#   default : used when no user value is present
#   desc    : shown as tooltip in the GUI  (include WHY and WHAT TO USE)
#   options : list of (value, label) → renders as selectbox
#   tip     : extra reasoning block shown below the widget as an info box
# ─────────────────────────────────────────────────────────────────────────────
PARAM_INFO: Dict[str, Dict[str, Any]] = {

    # ── Start / Restart ──────────────────────────────────────────────────────
    "ISTART": {
        "type": "int", "default": 0,
        "desc": (
            "Controls how VASP reads the initial wavefunction.\n"
            "• 0 = start from scratch (default for new calculations)\n"
            "• 1 = read WAVECAR (restart or non-SCF band/DOS)\n"
            "• 2 = read WAVECAR + charge density"
        ),
        "tip": "Use ISTART=0 for any fresh calculation. Use ISTART=1 when restarting "
               "from a previous run or when doing a non-self-consistent band/DOS calculation.",
        "options": [
            (0, "0 – Fresh start (no WAVECAR)"),
            (1, "1 – Read WAVECAR (restart / non-SCF)"),
            (2, "2 – Read WAVECAR + charge density"),
        ],
    },
    "ICHARG": {
        "type": "int", "default": 2,
        "desc": (
            "How the initial charge density is constructed.\n"
            "• 2 = superposition of atomic charge densities (best for fresh start)\n"
            "• 1 = read from CHGCAR file\n"
            "• 11 = non-SCF: keep charge density frozen (required for band structure & DOS)"
        ),
        "tip": "For band structure and DOS after an SCF run: use ICHARG=11. "
               "This keeps the charge density fixed so VASP only computes eigenvalues.",
        "options": [
            (2,  "2 – Atomic superposition (fresh start, recommended)"),
            (1,  "1 – Read from CHGCAR"),
            (0,  "0 – From WAVECAR"),
            (11, "11 – Non-SCF: frozen charge density (band / DOS)"),
        ],
    },

    # ── Electronic ───────────────────────────────────────────────────────────
    "ENCUT": {
        "type": "float", "default": 520.0,
        "desc": (
            "Plane-wave energy cutoff (eV).\n"
            "Rule: use 1.3 × max(ENMAX) from all POTCARs.\n"
            "The GUI suggests the correct value after you configure POTCAR in Step 4.\n"
            "Too low → unconverged; too high → slow."
        ),
        "tip": "Typical values: 400–500 eV for most elements. 520–600 eV for O, N, F. "
               "Always use the SAME ENCUT for all calculations you want to compare.",
    },
    "EDIFF": {
        "type": "str", "default": "1E-6",
        "desc": (
            "Electronic SCF convergence threshold (eV).\n"
            "• 1E-4 = fast, OK for ionic relaxation\n"
            "• 1E-5 = standard\n"
            "• 1E-6 = tight, needed before band/DOS/phonon"
        ),
        "tip": "Recommended: 1E-6 for any calculation where you will use the CHGCAR/WAVECAR "
               "for further analysis (band structure, DOS, phonons). 1E-5 is fine for "
               "pure structure relaxation.",
    },
    "PREC": {
        "type": "str", "default": "Accurate",
        "desc": (
            "Precision mode — affects FFT grid and basis set completeness.\n"
            "• Normal = fast, small grid\n"
            "• Accurate = larger grid, avoids aliasing errors (recommended)\n"
            "• High = very fine grid (needed for stress tensor calculations)"
        ),
        "tip": "Always use PREC=Accurate for production runs. Normal is only safe for "
               "quick pre-relaxation tests.",
        "options": [
            ("Low",      "Low – fast test runs only"),
            ("Normal",   "Normal – OK for pre-convergence tests"),
            ("Accurate", "Accurate – recommended for all production runs"),
            ("High",     "High – very fine grid, stress tensor calculations"),
        ],
    },
    "ALGO": {
        "type": "str", "default": "Normal",
        "desc": (
            "Electronic minimisation algorithm.\n"
            "• Normal = blocked Davidson (robust, good default)\n"
            "• Fast = RMM-DIIS (faster for metals, can diverge)\n"
            "• All = repeated Davidson + RMM-DIIS (for hard systems, hybrid, meta-GGA)\n"
            "• Damped = damped velocity friction (very stable but slow)\n"
            "• VeryFast = pure RMM-DIIS (fastest, least stable)"
        ),
        "tip": "Use Normal for most cases. Switch to All for hybrid (HSE06) and "
               "meta-GGA (MBJ, SCAN) functionals. Use Damped only if Normal/Fast fail.",
        "options": [
            ("Normal",   "Normal – Davidson (default, robust)"),
            ("Fast",     "Fast – RMM-DIIS (metals, faster)"),
            ("All",      "All – Davidson+RMM-DIIS (hybrid, meta-GGA)"),
            ("Damped",   "Damped – damped friction (very hard cases)"),
            ("VeryFast", "VeryFast – pure RMM-DIIS (fastest, unstable)"),
        ],
    },
    "NELM": {
        "type": "int", "default": 60,
        "desc": (
            "Maximum number of electronic SCF steps.\n"
            "• 60 = default, enough for most cases\n"
            "• 80–120 = for hard-to-converge systems (magnetic, strongly correlated)\n"
            "If NELM is reached without convergence, increase it or change ALGO."
        ),
    },
    "NELMIN": {
        "type": "int", "default": 2,
        "desc": (
            "Minimum number of electronic SCF steps (default 2).\n"
            "Increasing to 4–6 can help stabilise convergence at the start "
            "of a calculation when the initial density is far from self-consistency."
        ),
    },

    # ── Smearing ─────────────────────────────────────────────────────────────
    "ISMEAR": {
        "type": "int", "default": 0,
        "desc": (
            "Partial occupancy smearing method.\n"
            "• -5 = Tetrahedron (best for insulators/semiconductors, DOS; NOT for relaxation)\n"
            "• 0  = Gaussian (good general choice; band structure, semiconductors)\n"
            "• 1  = Methfessel-Paxton order 1 (metals — fast convergence with k-mesh)\n"
            "• 2  = M-P order 2 (metals, higher accuracy)"
        ),
        "tip": "Metals: ISMEAR=1, SIGMA=0.1–0.2. Semiconductors/insulators: ISMEAR=0, "
               "SIGMA=0.05 or ISMEAR=-5 (tetrahedron, only for static + dense k-mesh). "
               "Band structure: always ISMEAR=0, SIGMA=0.05.",
        "options": [
            (-5, "-5 – Tetrahedron (insulators/DOS, NOT relaxation)"),
            (-1, "-1 – Fermi-Dirac"),
            (0,  " 0 – Gaussian (general, band structure, semiconductors)"),
            (1,  " 1 – Methfessel-Paxton order 1 (metals)"),
            (2,  " 2 – Methfessel-Paxton order 2 (metals, more accurate)"),
        ],
    },
    "SIGMA": {
        "type": "float", "default": 0.05,
        "desc": (
            "Smearing width in eV.\n"
            "• Metals: 0.1–0.2 eV (wider → faster k-mesh convergence)\n"
            "• Semiconductors: 0.01–0.05 eV\n"
            "• Insulators: 0.01–0.05 eV\n"
            "Check: entropy term T*S in OUTCAR should be < 1 meV/atom."
        ),
        "tip": "If the smearing entropy (T*S) in OUTCAR exceeds 1 meV/atom, SIGMA is too large. "
               "For metals: try SIGMA=0.2 first, then reduce if needed.",
    },

    # ── Spin ─────────────────────────────────────────────────────────────────
    "ISPIN": {
        "type": "int", "default": 1,
        "desc": (
            "Spin polarisation.\n"
            "• 1 = non-spin-polarised (default)\n"
            "• 2 = spin-polarised (required for magnetic materials: Fe, Ni, Co, Mn, rare earths...)"
        ),
        "tip": "Set ISPIN=2 for any material containing 3d (Fe, Co, Ni, Mn, Cr) or 4f (rare earth) "
               "elements. Also set MAGMOM to initial magnetic moments.",
        "options": [(1, "1 – Non-spin-polarised"), (2, "2 – Spin-polarised (collinear)")],
    },
    "MAGMOM": {
        "type": "str", "default": "",
        "desc": (
            "Initial magnetic moments per atom (in μB).\n"
            "One value per atom, space-separated, in the same order as POSCAR.\n"
            "Examples:\n"
            "  Fe (BCC, 1 atom): MAGMOM = 4\n"
            "  Fe2O3 (5 atoms): MAGMOM = 5 5 5 0 0\n"
            "  Shorthand: 3*5 0 = 5 5 5 0"
        ),
        "tip": "Use MAGMOM to break spin symmetry. If you start non-magnetic and the system is "
               "magnetic, VASP may converge to a wrong non-magnetic state. Typical values: "
               "Fe≈4, Co≈3, Ni≈2, Mn≈5, Cr≈4.",
    },
    "LSORBIT": {
        "type": "bool", "default": False,
        "desc": (
            "Enable spin-orbit coupling (SOC).\n"
            "Required for: topological insulators, heavy elements (Bi, Pb, Au, Pt, W...),\n"
            "magnetic anisotropy, Rashba splitting.\n"
            "Must use vasp_ncl binary. Set LNONCOLLINEAR=.TRUE. as well."
        ),
        "tip": "SOC is expensive (~4× slower than scalar). Start with a scalar-relativistic "
               "SCF run, then restart with LSORBIT=.TRUE. and ICHARG=11.",
    },
    "LNONCOLLINEAR": {
        "type": "bool", "default": False,
        "desc": (
            "Enable non-collinear spin treatment.\n"
            "Required for: spin-orbit coupling, spin-spiral states, domain walls.\n"
            "Automatically enabled when LSORBIT=.TRUE."
        ),
    },

    # ── Output ───────────────────────────────────────────────────────────────
    "LORBIT": {
        "type": "int", "default": 11,
        "desc": (
            "Controls PROCAR and DOS output decomposition.\n"
            "• 0  = no PROCAR, no lm-decomposed DOS\n"
            "• 10 = write PROCAR (s, p, d, f per atom)\n"
            "• 11 = lm-decomposed DOS + PROCAR (px,py,pz,dxy... per atom) — recommended\n"
            "• 12 = same as 11 + phase factors (needed for fat-band projection)"
        ),
        "tip": "Use LORBIT=11 for most cases — gives you full orbital-projected DOS. "
               "Use LORBIT=12 only if you need fat-band plots with phase information.",
        "options": [
            (0,  "0 – No PROCAR / no l-decomposed DOS"),
            (10, "10 – PROCAR with s,p,d totals"),
            (11, "11 – lm-decomposed PROCAR + DOS (recommended)"),
            (12, "12 – lm-decomposed + phase factors (fat-band)"),
        ],
    },
    "LWAVE": {
        "type": "bool", "default": True,
        "desc": (
            "Write WAVECAR (wavefunctions).\n"
            "• .TRUE. = write WAVECAR (large file, needed to restart band/DOS/hybrid)\n"
            "• .FALSE. = skip (saves disk space, faster I/O)\n"
            "Keep .TRUE. for SCF runs that will be followed by band structure or DOS."
        ),
        "tip": "Always keep LWAVE=.TRUE. for SCF runs you plan to use for band/DOS/phonons. "
               "Set .FALSE. for relaxation runs to save disk space.",
    },
    "LCHARG": {
        "type": "bool", "default": True,
        "desc": (
            "Write CHGCAR (charge density).\n"
            "• .TRUE. = write CHGCAR (needed for band structure, DOS, charge analysis)\n"
            "• .FALSE. = skip (saves disk space)\n"
            "CHGCAR is required when ICHARG=11 (non-SCF band/DOS)."
        ),
        "tip": "Keep LCHARG=.TRUE. for SCF runs. You can safely set .FALSE. for "
               "relaxation runs where you don't need the charge density afterwards.",
    },
    "LVTOT": {
        "type": "bool", "default": False,
        "desc": (
            "Write total local potential (Hartree + XC + external) to LOCPOT.\n"
            "Required for: work function calculations, electrostatic potential analysis.\n"
            "Produces a large LOCPOT file."
        ),
    },
    "LVHAR": {
        "type": "bool", "default": False,
        "desc": "Write Hartree + XC potential to LOCPOT (without ionic potential).",
    },
    "NWRITE": {
        "type": "int", "default": 2,
        "desc": "Output verbosity (0=silent, 1=brief, 2=default, 3=verbose, 4=debug).",
        "options": [(0, "0 – Silent"), (1, "1 – Brief"), (2, "2 – Default"), (3, "3 – Verbose"), (4, "4 – Debug")],
    },

    # ── Parallelisation ──────────────────────────────────────────────────────
    "NCORE": {
        "type": "int", "default": 4,
        "desc": (
            "Number of CPU cores working on each orbital band.\n"
            "Rule: NCORE ≈ √(total MPI processes).\n"
            "Examples: 16 CPUs → NCORE=4; 36 CPUs → NCORE=6; 64 CPUs → NCORE=8.\n"
            "NCORE × KPAR must equal total MPI processes."
        ),
        "tip": "NCORE is the most important performance knob. Setting NCORE=1 uses purely "
               "k-point parallelism (good only if you have many k-points). "
               "NCORE=√N is usually optimal for band parallelism.",
    },
    "KPAR": {
        "type": "int", "default": 1,
        "desc": (
            "Parallelisation over k-point groups.\n"
            "• 1 = no k-point parallelism (default)\n"
            "• N = divide k-points into N groups (use when you have ≥ 2N k-points)\n"
            "KPAR × NCORE = total MPI processes."
        ),
        "tip": "Increase KPAR if you have many k-points. For a 4×4×4 mesh (64 irreducible "
               "k-points) with 32 MPI processes: try KPAR=2, NCORE=4 (8 cores per k-group).",
    },

    # ── Ionic / Relaxation ───────────────────────────────────────────────────
    "IBRION": {
        "type": "int", "default": -1,
        "desc": (
            "Ion update algorithm.\n"
            "• -1 = frozen ions (static calculation)\n"
            "• 1  = quasi-Newton / RMM-DIIS (near equilibrium, fast)\n"
            "• 2  = conjugate gradient (robust, for large displacements)\n"
            "• 0  = molecular dynamics\n"
            "• 5/6 = vibrational frequencies"
        ),
        "tip": "Use IBRION=2 (CG) as the safe default for relaxation. "
               "Switch to IBRION=1 once the structure is near equilibrium for faster convergence.",
        "options": [
            (-1, "-1 – Frozen ions (static)"),
            (0,  " 0 – Molecular dynamics"),
            (1,  " 1 – Quasi-Newton/RMM-DIIS (near-equilibrium, fast)"),
            (2,  " 2 – Conjugate gradient (robust, recommended)"),
            (3,  " 3 – Damped MD (difficult structures)"),
            (5,  " 5 – Vibrational frequencies (finite differences)"),
            (6,  " 6 – Vibrational frequencies (with symmetry)"),
        ],
    },
    "NSW": {
        "type": "int", "default": 0,
        "desc": (
            "Maximum number of ionic steps.\n"
            "• 0 = static (no ionic movement)\n"
            "• 100–200 = typical for ionic relaxation\n"
            "• 300–500 = for full cell relaxation\n"
            "VASP stops early if EDIFFG is satisfied before NSW is reached."
        ),
        "tip": "Set NSW=200 for ionic relaxation, NSW=300 for full cell relaxation. "
               "If relaxation hasn't converged at NSW, restart from CONTCAR.",
    },
    "EDIFFG": {
        "type": "str", "default": "-0.01",
        "desc": (
            "Ionic convergence criterion.\n"
            "• Negative value = max force threshold (eV/Å) — recommended\n"
            "  -0.02 eV/Å = standard; -0.01 eV/Å = tight; -0.001 eV/Å = very tight\n"
            "• Positive value = total energy change threshold (eV)\n"
            "  0.0001 eV = standard for energy convergence"
        ),
        "tip": "Use EDIFFG=-0.02 for most purposes. Use -0.01 for high-accuracy "
               "structures used in phonon calculations or NEB. "
               "Force-based (negative) is more reliable than energy-based.",
    },
    "ISIF": {
        "type": "int", "default": 2,
        "desc": (
            "Controls which degrees of freedom are relaxed.\n"
            "• 2 = relax ions, fixed cell shape & volume (most common)\n"
            "• 3 = relax ions + cell shape + volume (full relaxation)\n"
            "• 4 = relax ions + cell shape, fixed volume\n"
            "• 7 = fixed ions, relax volume only"
        ),
        "tip": "Use ISIF=2 first (ionic relaxation). Only switch to ISIF=3 after the "
               "ions are roughly relaxed. Full cell relaxation (ISIF=3) is slower and "
               "can cause issues with slab models — use ISIF=2 for slabs.",
        "options": [
            (0, "0 – Ions, no stress tensor"),
            (2, "2 – Ions only, fixed cell (most common)"),
            (3, "3 – Ions + cell shape + volume (full)"),
            (4, "4 – Ions + cell shape, fixed volume"),
            (5, "5 – Fixed ions, cell shape"),
            (6, "6 – Fixed ions, cell shape + volume"),
            (7, "7 – Fixed ions, volume only"),
        ],
    },
    "POTIM": {
        "type": "float", "default": 0.5,
        "desc": (
            "Step size for ionic moves (Å for IBRION=1,2,3; femtoseconds for IBRION=0 MD).\n"
            "• Relaxation: 0.3–0.5 Å (start conservative, increase if stable)\n"
            "• MD: 1–2 fs for light elements; 0.5–1 fs for heavy elements"
        ),
        "tip": "If ionic relaxation oscillates (energy going up/down), reduce POTIM. "
               "For MD, 2 fs is standard. Use 1 fs for hydrogen-containing systems.",
    },
    "ISYM": {
        "type": "int", "default": 2,
        "desc": (
            "Symmetry treatment.\n"
            "• 2 = use symmetry (default, reduces k-points and computation)\n"
            "• 1 = use symmetry without symmetrising forces\n"
            "• 0 = no symmetry (required for NEB, some surface calculations)"
        ),
        "options": [(0, "0 – Off (NEB, defects)"), (1, "1 – On"), (2, "2 – On + symmetrize forces (default)")],
    },

    # ── DOS ──────────────────────────────────────────────────────────────────
    "EMIN": {
        "type": "float", "default": -20.0,
        "desc": (
            "Minimum energy for DOS (absolute eV, NOT relative to Fermi level).\n"
            "Typical: Fermi energy − 15 eV. Check OUTCAR for E-Fermi first, "
            "then set EMIN = E_Fermi - 15."
        ),
        "tip": "The DOSCAR energy axis is in absolute eV. A typical Fermi level is around "
               "5–10 eV, so EMIN=-20, EMAX=10 usually covers the valence region well.",
    },
    "EMAX": {
        "type": "float", "default": 10.0,
        "desc": "Maximum energy for DOS (absolute eV). Typical: Fermi energy + 5–10 eV.",
    },
    "NEDOS": {
        "type": "int", "default": 3000,
        "desc": (
            "Number of energy grid points in the DOS.\n"
            "• 301 = default (too coarse for publications)\n"
            "• 2000–5000 = smooth DOS for plotting\n"
            "More points → smoother curve, negligible extra cost."
        ),
        "tip": "Always increase NEDOS to ≥2000 for publication-quality DOS plots. "
               "The default 301 produces a jagged curve.",
    },

    # ── DFT+U ────────────────────────────────────────────────────────────────
    "LDAU": {
        "type": "bool", "default": False,
        "desc": "Enable DFT+U Hubbard correction for correlated electrons (d, f orbitals).",
        "tip": "DFT+U is recommended for: transition metal oxides (FeO, NiO, CoO), "
               "rare-earth compounds, and any material where PBE severely underestimates "
               "the band gap. Use Dudarev formulation (LDAUTYPE=2) with U_eff = U - J.",
    },
    "LDAUTYPE": {
        "type": "int", "default": 2,
        "desc": (
            "DFT+U formulation.\n"
            "• 1 = Liechtenstein: separate U and J (more parameters)\n"
            "• 2 = Dudarev: single U_eff = U − J (most common, simpler)\n"
            "• 4 = Liechtenstein without exchange interaction"
        ),
        "tip": "Use LDAUTYPE=2 (Dudarev) — it's the most widely used and only requires "
               "one U value per species. Set LDAUJ=0 when using Dudarev.",
        "options": [
            (1, "1 – Liechtenstein (U and J separately)"),
            (2, "2 – Dudarev (U_eff = U−J, recommended)"),
            (4, "4 – Liechtenstein without J"),
        ],
    },
    "LDAUL": {
        "type": "str", "default": "",
        "desc": (
            "Angular momentum l for U correction, one value per species.\n"
            "• -1 = no correction\n"
            "• 0 = s orbital\n"
            "• 1 = p orbital\n"
            "• 2 = d orbital (transition metals)\n"
            "• 3 = f orbital (rare earths, actinides)\n"
            "Example: Fe2O3 → '2 -1' (U on Fe d, no U on O)"
        ),
    },
    "LDAUU": {
        "type": "str", "default": "",
        "desc": (
            "Hubbard U values (eV), one per species.\n"
            "Typical values: Fe=4–5, Co=3–4, Ni=6, Mn=3–4, V=3, Cu=7, Ce=5\n"
            "Example: Fe2O3 → '4.0 0.0' (U=4 on Fe, 0 on O)"
        ),
        "tip": "U values are material and property dependent. Common starting points: "
               "Fe(d)=4 eV, Co(d)=3.3 eV, Ni(d)=6.2 eV, Mn(d)=3.9 eV. "
               "Always check literature for your specific system.",
    },
    "LDAUJ": {
        "type": "str", "default": "",
        "desc": (
            "Hund's exchange J values (eV), one per species.\n"
            "For Dudarev (LDAUTYPE=2): set all to 0 — J is absorbed into U_eff.\n"
            "For Liechtenstein (LDAUTYPE=1): typical J ≈ 0.6–1 eV for 3d metals."
        ),
    },

    # ── Meta-GGA ─────────────────────────────────────────────────────────────
    "METAGGA": {
        "type": "str", "default": "",
        "desc": (
            "Meta-GGA functional. Leave blank for standard GGA.\n"
            "• MBJ   = modified Becke-Johnson — excellent band gaps, cheap, NO total energy\n"
            "• SCAN  = Strongly Constrained and Appropriately Normed — accurate but slow\n"
            "• R2SCAN = regularised SCAN — nearly as accurate, more stable (recommended)\n"
            "• TPSS  = Tao-Perdew-Staroverov-Scuseria\n"
            "• M06L  = Minnesota M06-L"
        ),
        "tip": (
            "R2SCAN is the best all-round meta-GGA for production use. "
            "MBJ is the go-to choice for band gaps of semiconductors at low cost "
            "(comparable to HSE06 at GGA cost), but cannot be used for total energies or forces. "
            "Always set LASPH=.TRUE. and ALGO=All with meta-GGA."
        ),
        "options": [
            ("",       "None – standard GGA/LDA"),
            ("MBJ",    "MBJ – modified Becke-Johnson (band gaps only, no energy)"),
            ("R2SCAN", "R2SCAN – regularised SCAN (recommended meta-GGA)"),
            ("SCAN",   "SCAN – Strongly Constrained and Appropriately Normed"),
            ("TPSS",   "TPSS – Tao-Perdew-Staroverov-Scuseria"),
            ("RTPSS",  "RTPSS – revised TPSS"),
            ("M06L",   "M06-L – Minnesota M06-L"),
            ("MS0",    "MS0 – made-simple 0"),
            ("MS1",    "MS1 – made-simple 1"),
            ("MS2",    "MS2 – made-simple 2"),
        ],
    },
    "CMBJ": {
        "type": "float", "default": -1.0,
        "desc": (
            "MBJ c parameter (only used when METAGGA=MBJ).\n"
            "• -1 = auto-determined from average electron density (recommended)\n"
            "• 1.0–1.3 = manual override (rarely needed)\n"
            "The auto value is usually optimal."
        ),
        "tip": "Leave CMBJ=-1 (auto). The automatic c value is determined self-consistently "
               "from the electron density and gives the best band gaps for most semiconductors.",
    },
    "LASPH": {
        "type": "bool", "default": False,
        "desc": (
            "Include non-spherical contributions to PAW one-centre terms.\n"
            "REQUIRED for: meta-GGA (MBJ, SCAN, R2SCAN), DFT+U with J, exact exchange.\n"
            "Slightly increases computation time but improves accuracy."
        ),
        "tip": "Always set LASPH=.TRUE. when using meta-GGA or DFT+U. "
               "Forgetting this is a common mistake that gives wrong results.",
    },

    # ── Hybrid (HSE06) ───────────────────────────────────────────────────────
    "LHFCALC": {
        "type": "bool", "default": False,
        "desc": (
            "Enable Hartree-Fock (exact) exchange.\n"
            "Required for hybrid functionals: HSE06, PBE0.\n"
            "Must use ALGO=All for hybrids."
        ),
        "tip": "HSE06 (LHFCALC=.TRUE., AEXX=0.25, HFSCREEN=0.2) is the standard "
               "for accurate band gaps. It costs ~10× more than PBE. "
               "Always start from a converged PBE WAVECAR (ISTART=1, ICHARG=1).",
    },
    "AEXX": {
        "type": "float", "default": 0.25,
        "desc": (
            "Fraction of exact Hartree-Fock exchange mixed into DFT.\n"
            "• HSE06 = 0.25 (standard, 25% HF exchange)\n"
            "• PBE0  = 0.25 (unscreened, HFSCREEN=0)\n"
            "• Tuning: increase for wider gap materials"
        ),
    },
    "HFSCREEN": {
        "type": "float", "default": 0.2,
        "desc": (
            "Screening parameter for the range-separated HF exchange (Å⁻¹).\n"
            "• 0   = PBE0 (no screening, expensive for metals)\n"
            "• 0.2 = HSE06 (screened, recommended for solids)\n"
            "HSE06 converges faster with k-points than PBE0."
        ),
    },

    # ── vdW ──────────────────────────────────────────────────────────────────
    "IVDW": {
        "type": "int", "default": 0,
        "desc": (
            "van der Waals dispersion correction.\n"
            "• 0   = None (default)\n"
            "• 11  = DFT-D3 zero damping\n"
            "• 12  = DFT-D3 with Becke-Johnson damping (recommended for most cases)\n"
            "• 20  = Tkatchenko-Scheffler (TS)\n"
            "• 202 = Many-body dispersion (MBD-rSCS, most accurate, slowest)"
        ),
        "tip": "Use IVDW=12 (DFT-D3/BJ) for layered materials, molecular crystals, "
               "and any system with significant van der Waals interactions. "
               "MBD (IVDW=202) is more accurate but ~3× slower.",
        "options": [
            (0,   "0 – None"),
            (11,  "11 – DFT-D3 (zero damping)"),
            (12,  "12 – DFT-D3 with BJ damping (recommended)"),
            (20,  "20 – Tkatchenko-Scheffler"),
            (21,  "21 – TS with iterative Hirshfeld"),
            (202, "202 – Many-body dispersion (MBD, most accurate)"),
        ],
    },

    # ── MD ───────────────────────────────────────────────────────────────────
    "MDALGO": {
        "type": "int", "default": 2,
        "desc": (
            "MD thermostat/barostat algorithm.\n"
            "• 0 = NVE microcanonical (Verlet, no thermostat)\n"
            "• 1 = NVT Andersen thermostat (stochastic)\n"
            "• 2 = NVT Nosé-Hoover thermostat (recommended, conserves energy drift)\n"
            "• 3 = NVT Langevin thermostat (good for equilibration)"
        ),
        "options": [
            (0, "0 – NVE microcanonical (Verlet)"),
            (1, "1 – NVT Andersen thermostat"),
            (2, "2 – NVT Nosé-Hoover (recommended)"),
            (3, "3 – NVT Langevin"),
        ],
    },
    "TEBEG": {
        "type": "float", "default": 300.0,
        "desc": "Starting temperature for MD (K). Typical: 300 K (room temperature).",
    },
    "TEEND": {
        "type": "float", "default": 300.0,
        "desc": "Ending temperature for MD (K). Set equal to TEBEG for NVT at constant T.",
    },
    "SMASS": {
        "type": "float", "default": 0.0,
        "desc": (
            "Nosé-Hoover thermostat mass parameter.\n"
            "• 0 = auto (VASP determines optimal mass from temperature and POTIM)\n"
            "Rarely needs manual tuning — keep at 0."
        ),
    },
    "NBLOCK": {
        "type": "int", "default": 1,
        "desc": "Steps between partial averages written to OSZICAR (default 1).",
    },
    "KBLOCK": {
        "type": "int", "default": 10,
        "desc": "XDATCAR (ionic trajectory) is written every KBLOCK × NBLOCK steps.",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Calculation templates
# ─────────────────────────────────────────────────────────────────────────────
CALC_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "scf": {
        "label": "Static SCF", "icon": "⚡",
        "desc": (
            "Self-consistent electronic structure at fixed geometry. "
            "This is the foundation — run SCF first to get CHGCAR/WAVECAR, "
            "then use them for band structure, DOS, or hybrid calculations."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "Static SCF",
            "ISTART": 0, "ICHARG": 2,
            "ENCUT": 520.0, "EDIFF": "1E-6",
            "PREC": "Accurate", "ALGO": "Normal",
            "NELM": 60, "NELMIN": 2,
            "ISMEAR": 0, "SIGMA": 0.05,
            "LORBIT": 11,
            "LWAVE": ".TRUE.", "LCHARG": ".TRUE.",
            "NCORE": 4,
        },
    },
    "relax_ions": {
        "label": "Ionic Relaxation", "icon": "🔄",
        "desc": (
            "Relax atomic positions at fixed cell shape and volume. "
            "First step for any new structure before doing electronic properties."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "Ionic relaxation",
            "ISTART": 0, "ICHARG": 2,
            "ENCUT": 520.0, "EDIFF": "1E-5",
            "PREC": "Accurate", "ALGO": "Normal",
            "NELM": 60, "NELMIN": 2,
            "ISMEAR": 0, "SIGMA": 0.05,
            "IBRION": 2, "NSW": 200,
            "EDIFFG": "-0.02", "ISIF": 2, "POTIM": 0.5,
            "LORBIT": 11,
            "LWAVE": ".FALSE.", "LCHARG": ".FALSE.",
            "NCORE": 4,
        },
    },
    "relax_full": {
        "label": "Full Relaxation (ions + cell)", "icon": "🔁",
        "desc": (
            "Relax everything: atomic positions, cell shape, and volume. "
            "Use for bulk structure optimisation from scratch."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "Full relaxation",
            "ISTART": 0, "ICHARG": 2,
            "ENCUT": 520.0, "EDIFF": "1E-5",
            "PREC": "Accurate", "ALGO": "Normal",
            "NELM": 60, "NELMIN": 2,
            "ISMEAR": 0, "SIGMA": 0.05,
            "IBRION": 2, "NSW": 300,
            "EDIFFG": "-0.01", "ISIF": 3, "POTIM": 0.3,
            "LORBIT": 11,
            "LWAVE": ".FALSE.", "LCHARG": ".FALSE.",
            "NCORE": 4,
        },
    },
    "band": {
        "label": "Band Structure", "icon": "📈",
        "desc": (
            "Non-self-consistent calculation along high-symmetry k-paths. "
            "Requires CHGCAR (and optionally WAVECAR) from a prior SCF run. "
            "Set KPOINTS to line-mode in Step 3."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "Band structure",
            "ISTART": 1, "ICHARG": 11,
            "ENCUT": 520.0, "EDIFF": "1E-6",
            "PREC": "Accurate", "ALGO": "Normal",
            "NELM": 1, "NELMIN": 1,
            "ISMEAR": 0, "SIGMA": 0.05,
            "LORBIT": 11,
            "LWAVE": ".FALSE.", "LCHARG": ".FALSE.",
            "NCORE": 4,
        },
    },
    "dos": {
        "label": "Density of States (DOS)", "icon": "📊",
        "desc": (
            "Non-self-consistent DOS with a fine k-mesh and lm-decomposed projections. "
            "Requires CHGCAR from a prior SCF run. Use a denser k-mesh than SCF."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "DOS calculation",
            "ISTART": 1, "ICHARG": 11,
            "ENCUT": 520.0, "EDIFF": "1E-6",
            "PREC": "Accurate", "ALGO": "Normal",
            "NELM": 1, "NELMIN": 1,
            "ISMEAR": -5, "SIGMA": 0.05,
            "LORBIT": 11,
            "EMIN": -20.0, "EMAX": 10.0, "NEDOS": 3000,
            "LWAVE": ".FALSE.", "LCHARG": ".FALSE.",
            "NCORE": 4,
        },
    },
    "mbj": {
        "label": "mBJ (band gap — meta-GGA)", "icon": "🎯",
        "desc": (
            "Modified Becke-Johnson meta-GGA for accurate band gaps at low cost. "
            "Comparable accuracy to HSE06 but much cheaper. "
            "⚠️ mBJ gives no ground-state total energy or forces — use only for electronic structure. "
            "Run PBE SCF first to get CHGCAR."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "mBJ meta-GGA band gap",
            "ISTART": 1, "ICHARG": 11,
            "ENCUT": 520.0, "EDIFF": "1E-6",
            "PREC": "Accurate", "ALGO": "All",
            "NELM": 80,
            "ISMEAR": 0, "SIGMA": 0.05,
            "METAGGA": "MBJ", "CMBJ": -1.0, "LASPH": ".TRUE.",
            "LORBIT": 11,
            "LWAVE": ".FALSE.", "LCHARG": ".FALSE.",
            "NCORE": 4,
        },
    },
    "r2scan": {
        "label": "R2SCAN (meta-GGA)", "icon": "🔬",
        "desc": (
            "Regularised SCAN meta-GGA — more accurate than PBE for structures, "
            "energetics, and band gaps. More stable than SCAN. Good all-round choice."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "R2SCAN meta-GGA",
            "ISTART": 0, "ICHARG": 2,
            "ENCUT": 520.0, "EDIFF": "1E-6",
            "PREC": "Accurate", "ALGO": "All",
            "NELM": 80,
            "ISMEAR": 0, "SIGMA": 0.05,
            "METAGGA": "R2SCAN", "LASPH": ".TRUE.",
            "LORBIT": 11,
            "LWAVE": ".TRUE.", "LCHARG": ".TRUE.",
            "NCORE": 4,
        },
    },
    "md_nvt": {
        "label": "Molecular Dynamics (NVT)", "icon": "🌡️",
        "desc": (
            "Ab initio MD at constant temperature and volume using Nosé-Hoover thermostat. "
            "Typical: 2 fs time step, 300 K, 2000–5000 steps."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "NVT MD",
            "ISTART": 0, "ICHARG": 2,
            "ENCUT": 520.0, "EDIFF": "1E-5",
            "PREC": "Normal", "ALGO": "Fast",
            "NELM": 60,
            "ISMEAR": 0, "SIGMA": 0.1,
            "IBRION": 0, "NSW": 2000,
            "POTIM": 2.0,
            "MDALGO": 2, "TEBEG": 300.0, "TEEND": 300.0,
            "SMASS": 0.0, "NBLOCK": 1, "KBLOCK": 10,
            "ISIF": 2,
            "LWAVE": ".FALSE.", "LCHARG": ".FALSE.",
            "NCORE": 4,
        },
    },
    "hse06": {
        "label": "HSE06 Hybrid Functional", "icon": "💎",
        "desc": (
            "Screened hybrid HSE06 for accurate band gaps and electronic structure. "
            "~10× more expensive than PBE. "
            "Start from a converged PBE WAVECAR (ISTART=1, ICHARG=1) to save time."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "HSE06 hybrid",
            "ISTART": 1, "ICHARG": 1,
            "ENCUT": 520.0, "EDIFF": "1E-5",
            "PREC": "Accurate", "ALGO": "All",
            "NELM": 80,
            "ISMEAR": 0, "SIGMA": 0.05,
            "LHFCALC": ".TRUE.", "AEXX": 0.25, "HFSCREEN": 0.2,
            "LORBIT": 11,
            "LWAVE": ".TRUE.", "LCHARG": ".TRUE.",
            "NCORE": 4,
        },
    },
    "soc": {
        "label": "Spin-Orbit Coupling (SOC)", "icon": "🌀",
        "desc": (
            "Non-collinear SOC for heavy-element compounds (Bi, Pb, W, Pt, Au...) "
            "and topological materials. "
            "Requires vasp_ncl binary and CHGCAR from prior scalar-relativistic SCF."
        ),
        "vasp_bin": "vasp_ncl",
        "params": {
            "SYSTEM": "SOC calculation",
            "ISTART": 1, "ICHARG": 11,
            "ENCUT": 520.0, "EDIFF": "1E-6",
            "PREC": "Accurate", "ALGO": "Normal",
            "NELM": 60,
            "ISMEAR": 0, "SIGMA": 0.05,
            "LSORBIT": ".TRUE.", "LNONCOLLINEAR": ".TRUE.",
            "LORBIT": 11,
            "LWAVE": ".FALSE.", "LCHARG": ".FALSE.",
            "NCORE": 4,
        },
    },
    "dftu": {
        "label": "DFT+U (Hubbard U correction)", "icon": "🧲",
        "desc": (
            "GGA+U for strongly correlated systems (transition metal oxides, rare earths). "
            "Dudarev formulation (LDAUTYPE=2) with a single U_eff per species is recommended."
        ),
        "vasp_bin": "vasp_std",
        "params": {
            "SYSTEM": "DFT+U",
            "ISTART": 0, "ICHARG": 2,
            "ENCUT": 520.0, "EDIFF": "1E-6",
            "PREC": "Accurate", "ALGO": "Normal",
            "NELM": 80, "NELMIN": 4,
            "ISMEAR": 0, "SIGMA": 0.05,
            "ISPIN": 2,
            "LDAU": ".TRUE.", "LDAUTYPE": 2,
            "LDAUL": "", "LDAUU": "", "LDAUJ": "",
            "LASPH": ".TRUE.",
            "LORBIT": 11,
            "LWAVE": ".TRUE.", "LCHARG": ".TRUE.",
            "NCORE": 4,
        },
    },
}


def render_incar(params: Dict[str, Any]) -> str:
    """Convert a parameter dict to INCAR file text, grouped by category."""
    lines = []
    system = params.get("SYSTEM", "VASP calculation")
    lines.append(f"SYSTEM = {system}")
    lines.append("")

    categories = [
        ("# — Start / Restart",    ["ISTART", "ICHARG"]),
        ("# — Electronic",         ["ENCUT", "EDIFF", "PREC", "ALGO", "NELM", "NELMIN"]),
        ("# — Smearing",           ["ISMEAR", "SIGMA"]),
        ("# — Meta-GGA",           ["METAGGA", "CMBJ", "LASPH"]),
        ("# — Spin",               ["ISPIN", "MAGMOM", "LSORBIT", "LNONCOLLINEAR"]),
        ("# — Ionic / Relaxation", ["IBRION", "NSW", "EDIFFG", "ISIF", "POTIM", "ISYM"]),
        ("# — MD",                 ["MDALGO", "TEBEG", "TEEND", "SMASS", "NBLOCK", "KBLOCK"]),
        ("# — DOS",                ["EMIN", "EMAX", "NEDOS"]),
        ("# — DFT+U",              ["LDAU", "LDAUTYPE", "LDAUL", "LDAUU", "LDAUJ"]),
        ("# — Hybrid",             ["LHFCALC", "AEXX", "HFSCREEN"]),
        ("# — van der Waals",      ["IVDW"]),
        ("# — Output",             ["LORBIT", "LWAVE", "LCHARG", "LVTOT", "LVHAR", "NWRITE"]),
        ("# — Parallelisation",    ["NCORE", "KPAR"]),
    ]

    written = {"SYSTEM"}
    for header, keys in categories:
        section_lines = []
        for k in keys:
            if k in params and k not in written:
                v = params[k]
                if v == "" or v is None:
                    continue
                section_lines.append(f"  {k} = {v}")
                written.add(k)
        if section_lines:
            lines.append(header)
            lines.extend(section_lines)
            lines.append("")

    # Remaining unclassified keys
    extra = [(k, v) for k, v in params.items() if k not in written and v != "" and v is not None]
    if extra:
        lines.append("# — Extra")
        for k, v in extra:
            lines.append(f"  {k} = {v}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
