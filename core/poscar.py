"""POSCAR file utilities."""
from __future__ import annotations
import io
import math
import re
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from pymatgen.core import Structure
    from pymatgen.io.vasp import Poscar
    from pymatgen.io.cif import CifParser
    HAS_PYMATGEN = True
except ImportError:
    HAS_PYMATGEN = False


# ─── Parsing ─────────────────────────────────────────────────────────────────

def parse_poscar(text: str) -> Dict:
    """Return dict with structure info from POSCAR text."""
    lines = [ln for ln in text.splitlines()]
    if len(lines) < 7:
        raise ValueError("File too short to be a POSCAR.")

    comment = lines[0].strip()
    scale = float(lines[1].strip())
    a1 = [float(x) for x in lines[2].split()]
    a2 = [float(x) for x in lines[3].split()]
    a3 = [float(x) for x in lines[4].split()]

    # Line 5: species names or ion counts
    parts5 = lines[5].split()
    try:
        counts = [int(x) for x in parts5]
        species: List[str] = []
        coord_start = 6
    except ValueError:
        species = list(parts5)
        counts = [int(x) for x in lines[6].split()]
        coord_start = 7

    if coord_start >= len(lines):
        raise ValueError("Missing coordinate type line.")

    coord_type = lines[coord_start].strip()

    positions: List[List[float]] = []
    total = sum(counts)
    for i in range(total):
        idx = coord_start + 1 + i
        if idx >= len(lines):
            break
        pos = [float(x) for x in lines[idx].split()[:3]]
        positions.append(pos)

    return {
        "comment": comment,
        "scale": scale,
        "lattice": [a1, a2, a3],
        "species": species,
        "counts": counts,
        "coord_type": coord_type,
        "positions": positions,
    }


def get_elements(poscar_text: str) -> List[str]:
    """Return element symbols from POSCAR."""
    lines = poscar_text.strip().splitlines()
    if len(lines) < 6:
        return []
    parts = lines[5].split()
    try:
        int(parts[0])
        return []
    except ValueError:
        return parts


def poscar_info(poscar_text: str) -> Dict:
    """Return human-readable structure info."""
    try:
        d = parse_poscar(poscar_text)
    except Exception as e:
        return {"error": str(e)}

    elems = d["species"]
    counts = d["counts"]
    n_atoms = sum(counts)

    if elems:
        formula = "".join(f"{e}{n if n > 1 else ''}" for e, n in zip(elems, counts))
    else:
        formula = f"? ({n_atoms} atoms)"

    scale = d["scale"]
    latt = d["lattice"]

    if HAS_NUMPY:
        a = np.array(latt) * scale
        lengths = [float(np.linalg.norm(v)) for v in a]
        vol = float(abs(np.dot(a[0], np.cross(a[1], a[2]))))
        # angles
        def angle(v1, v2):
            c = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
            return math.degrees(math.acos(max(-1, min(1, c))))
        alpha = angle(a[1], a[2])
        beta  = angle(a[0], a[2])
        gamma = angle(a[0], a[1])
    else:
        lengths = [math.sqrt(sum(x**2 for x in v)) * scale for v in latt]
        vol = 0.0
        alpha = beta = gamma = 90.0

    return {
        "formula": formula,
        "elements": elems,
        "counts": counts,
        "n_atoms": n_atoms,
        "a": lengths[0], "b": lengths[1], "c": lengths[2],
        "alpha": alpha, "beta": beta, "gamma": gamma,
        "volume": vol,
    }


# ─── CIF → POSCAR ────────────────────────────────────────────────────────────

def cif_to_poscar(cif_content: bytes, primitive: bool = False) -> str:
    """Convert CIF bytes to POSCAR string using pymatgen."""
    if not HAS_PYMATGEN:
        raise ImportError("pymatgen is required for CIF import. Install with: pip install pymatgen")
    with tempfile.NamedTemporaryFile(suffix=".cif", delete=False) as f:
        f.write(cif_content)
        tmp = f.name
    try:
        parser = CifParser(tmp)
        structs = parser.parse_structures(primitive=primitive)
        if not structs:
            raise ValueError("No structures found in CIF file.")
        structure = structs[0]
        poscar = Poscar(structure)
        return str(poscar)
    finally:
        os.unlink(tmp)


# ─── Common structures ───────────────────────────────────────────────────────

COMMON_STRUCTURES: Dict[str, Dict] = {
    "Si (FCC diamond, cubic)": {
        "poscar": """\
Si diamond cubic
1.0
   0.000000   2.715000   2.715000
   2.715000   0.000000   2.715000
   2.715000   2.715000   0.000000
Si
2
Direct
  0.000000  0.000000  0.000000
  0.250000  0.250000  0.250000
""",
    },
    "Fe (BCC, magnetic)": {
        "poscar": """\
Fe BCC
1.0
  -1.435000   1.435000   1.435000
   1.435000  -1.435000   1.435000
   1.435000   1.435000  -1.435000
Fe
1
Direct
  0.000000  0.000000  0.000000
""",
    },
    "Cu (FCC)": {
        "poscar": """\
Cu FCC
1.0
   0.000000   1.805000   1.805000
   1.805000   0.000000   1.805000
   1.805000   1.805000   0.000000
Cu
1
Direct
  0.000000  0.000000  0.000000
""",
    },
    "Al (FCC)": {
        "poscar": """\
Al FCC
1.0
   0.000000   2.025000   2.025000
   2.025000   0.000000   2.025000
   2.025000   2.025000   0.000000
Al
1
Direct
  0.000000  0.000000  0.000000
""",
    },
    "NaCl (rock-salt)": {
        "poscar": """\
NaCl rock-salt
1.0
   2.820000   0.000000   2.820000
   2.820000   2.820000   0.000000
   0.000000   2.820000   2.820000
Na Cl
1 1
Direct
  0.000000  0.000000  0.000000
  0.500000  0.500000  0.500000
""",
    },
    "TiO2 (rutile)": {
        "poscar": """\
TiO2 rutile
1.0
   4.593000   0.000000   0.000000
   0.000000   4.593000   0.000000
   0.000000   0.000000   2.959000
Ti O
2 4
Direct
  0.000000  0.000000  0.000000
  0.500000  0.500000  0.500000
  0.305000  0.305000  0.000000
  0.805000 -0.195000  0.500000
 -0.195000  0.805000  0.500000
 -0.305000 -0.305000  0.000000
""",
    },
    "Graphene (2D hexagonal)": {
        "poscar": """\
Graphene
1.0
   2.466000   0.000000   0.000000
  -1.233000   2.136000   0.000000
   0.000000   0.000000  20.000000
C
2
Direct
  0.000000  0.000000  0.500000
  0.333333  0.666667  0.500000
""",
    },
}
