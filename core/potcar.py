"""POTCAR assembly utilities."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

POTCAR_DIRS: Dict[str, Path] = {
    "PBE": Path("/home/shahi/software/gnu/VASP/VASP/potpaw_PBE.64"),
    "LDA": Path("/home/shahi/software/gnu/VASP/VASP/potpaw_LDA.64"),
}

# Recommended standard variants (prefer _pv or _sv for transition metals)
RECOMMENDED: Dict[str, str] = {
    "H":  "H",   "He": "He",  "Li": "Li_sv", "Be": "Be",
    "B":  "B",   "C":  "C",   "N":  "N",     "O":  "O",
    "F":  "F",   "Ne": "Ne",  "Na": "Na_pv", "Mg": "Mg",
    "Al": "Al",  "Si": "Si",  "P":  "P",     "S":  "S",
    "Cl": "Cl",  "Ar": "Ar",  "K":  "K_sv",  "Ca": "Ca_sv",
    "Sc": "Sc_sv", "Ti": "Ti_sv", "V": "V_sv", "Cr": "Cr_pv",
    "Mn": "Mn_pv", "Fe": "Fe_pv", "Co": "Co",  "Ni": "Ni",
    "Cu": "Cu",  "Zn": "Zn",  "Ga": "Ga_d",  "Ge": "Ge_d",
    "As": "As",  "Se": "Se",  "Br": "Br",    "Kr": "Kr",
    "Rb": "Rb_sv", "Sr": "Sr_sv", "Y": "Y_sv", "Zr": "Zr_sv",
    "Nb": "Nb_pv", "Mo": "Mo_pv", "Tc": "Tc_pv", "Ru": "Ru_pv",
    "Rh": "Rh_pv", "Pd": "Pd",  "Ag": "Ag",  "Cd": "Cd",
    "In": "In_d",  "Sn": "Sn_d", "Sb": "Sb",  "Te": "Te",
    "I":  "I",   "Xe": "Xe",  "Cs": "Cs_sv", "Ba": "Ba_sv",
    "La": "La",  "Ce": "Ce",  "Pr": "Pr_3",  "Nd": "Nd_3",
    "Sm": "Sm_3", "Eu": "Eu_2", "Gd": "Gd",  "Tb": "Tb_3",
    "Dy": "Dy_3", "Ho": "Ho_3", "Er": "Er_3", "Tm": "Tm_3",
    "Yb": "Yb_2", "Lu": "Lu_3", "Hf": "Hf_pv", "Ta": "Ta_pv",
    "W":  "W_pv", "Re": "Re",  "Os": "Os",  "Ir": "Ir",
    "Pt": "Pt",  "Au": "Au",  "Hg": "Hg",  "Tl": "Tl_d",
    "Pb": "Pb_d", "Bi": "Bi_d", "Po": "Po_d", "At": "At_d",
    "Rn": "Rn",
}


def get_available_variants(element: str, functional: str = "PBE") -> List[str]:
    """Return list of available POTCAR directory names for this element."""
    potcar_dir = POTCAR_DIRS.get(functional)
    if potcar_dir is None or not potcar_dir.exists():
        return []
    pattern = re.compile(rf"^{re.escape(element)}(_|$)")
    variants = [
        d.name for d in potcar_dir.iterdir()
        if d.is_dir() and pattern.match(d.name) and (d / "POTCAR").exists()
    ]
    return sorted(variants)


def get_recommended_variant(element: str, functional: str = "PBE") -> Optional[str]:
    """Return recommended POTCAR variant for element, fallback to plain element."""
    rec = RECOMMENDED.get(element, element)
    available = get_available_variants(element, functional)
    if not available:
        return None
    if rec in available:
        return rec
    if element in available:
        return element
    return available[0]


def get_enmax(element: str, variant: str, functional: str = "PBE") -> Optional[float]:
    """Read ENMAX from an individual POTCAR file."""
    potcar_dir = POTCAR_DIRS.get(functional)
    if potcar_dir is None:
        return None
    potcar_path = potcar_dir / variant / "POTCAR"
    if not potcar_path.exists():
        return None
    try:
        with potcar_path.open("r", errors="replace") as f:
            for line in f:
                if "ENMAX" in line:
                    m = re.search(r"ENMAX\s*=\s*([\d.]+)", line)
                    if m:
                        return float(m.group(1))
    except Exception:
        pass
    return None


def assemble_potcar(
    elements: List[str],
    variants: Dict[str, str],
    functional: str = "PBE",
    output_path: Optional[Path] = None,
) -> str:
    """Concatenate individual POTCAR files into one.

    Returns the path of the written POTCAR, or raises an error.
    """
    potcar_dir = POTCAR_DIRS.get(functional)
    if potcar_dir is None:
        raise ValueError(f"Unknown functional: {functional}")
    if not potcar_dir.exists():
        raise FileNotFoundError(f"POTCAR directory not found: {potcar_dir}")

    chunks: List[str] = []
    for elem in elements:
        variant = variants.get(elem, elem)
        src = potcar_dir / variant / "POTCAR"
        if not src.exists():
            raise FileNotFoundError(f"POTCAR not found for {elem} (variant={variant}): {src}")
        chunks.append(src.read_text(errors="replace"))

    content = "".join(chunks)
    if output_path is not None:
        output_path.write_text(content, errors="replace")
    return content


def suggest_encut(elements: List[str], variants: Dict[str, str], functional: str = "PBE") -> Optional[float]:
    """Suggest ENCUT = 1.3 × max(ENMAX) from selected POTCARs."""
    enmax_vals = []
    for elem in elements:
        variant = variants.get(elem, elem)
        v = get_enmax(elem, variant, functional)
        if v is not None:
            enmax_vals.append(v)
    if not enmax_vals:
        return None
    return round(1.3 * max(enmax_vals), 0)
