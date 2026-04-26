"""VASP job runner and output parser."""
from __future__ import annotations
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

VASP_BIN_DIR = Path("/home/shahi/software/gnu/VASP/VASP/vasp.6.5.1/bin")
VASP_BINS = {
    "vasp_std": VASP_BIN_DIR / "vasp_std",
    "vasp_gam": VASP_BIN_DIR / "vasp_gam",
    "vasp_ncl": VASP_BIN_DIR / "vasp_ncl",
}

_float_re = r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?"


def check_vasp_available() -> Dict[str, bool]:
    return {name: path.exists() for name, path in VASP_BINS.items()}


def run_vasp(
    work_dir: Path,
    binary: str = "vasp_std",
    np: int = 4,
    omp: int = 1,
) -> subprocess.Popen:
    """Launch VASP and return the Popen handle (non-blocking)."""
    work_dir = Path(work_dir)
    bin_path = VASP_BINS.get(binary)
    if bin_path is None or not bin_path.exists():
        raise FileNotFoundError(f"VASP binary not found: {binary} ({bin_path})")

    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(omp)

    cmd = ["mpirun", "-np", str(np), str(bin_path)]

    proc = subprocess.Popen(
        cmd,
        cwd=str(work_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


def tail_oszicar(work_dir: Path, max_lines: int = 30) -> List[str]:
    """Return last N lines of OSZICAR."""
    path = Path(work_dir) / "OSZICAR"
    if not path.exists():
        return []
    lines = path.read_text(errors="replace").splitlines()
    return lines[-max_lines:]


def tail_outcar(work_dir: Path, max_lines: int = 50) -> List[str]:
    """Return last N lines of OUTCAR."""
    path = Path(work_dir) / "OUTCAR"
    if not path.exists():
        return []
    lines = path.read_text(errors="replace").splitlines()
    return lines[-max_lines:]


def parse_oszicar(work_dir: Path) -> List[Dict]:
    """Parse OSZICAR energy steps."""
    path = Path(work_dir) / "OSZICAR"
    if not path.exists():
        return []
    steps = []
    for line in path.read_text(errors="replace").splitlines():
        # DAV / RMM steps
        m = re.match(r"\s*(\w+)\s+(\d+)\s+([-\d.E+]+)\s+([-\d.E+]+)\s+([-\d.E+]+)\s+([-\d.E+]+)\s+([-\d.E+]+)", line)
        if m:
            try:
                steps.append({
                    "type": m.group(1),
                    "iter": int(m.group(2)),
                    "E": float(m.group(3)),
                    "dE": float(m.group(4)),
                })
            except ValueError:
                pass
    return steps


def parse_outcar_summary(work_dir: Path) -> Dict:
    """Extract key results from OUTCAR."""
    path = Path(work_dir) / "OUTCAR"
    if not path.exists():
        return {}

    result: Dict = {}
    toten_re   = re.compile(r"free\s+energy\s+TOTEN\s*=\s*(" + _float_re + r")")
    efermi_re  = re.compile(r"E-fermi\s*:\s*(" + _float_re + r")")
    nelect_re  = re.compile(r"\bNELECT\b\s*=\s*(" + _float_re + r")")
    nkpts_re   = re.compile(r"\bNKPTS\b\s*=\s*(\d+)")
    nbands_re  = re.compile(r"\bNBANDS\b\s*=\s*(\d+)")
    force_re   = re.compile(r"FORCES:\s+max=\s*(" + _float_re + r")\s+RMS=\s*(" + _float_re + r")")
    mag_re     = re.compile(r"number of electron\s+[\d.]+\s+magnetization\s+(" + _float_re + r")")
    converg_re = re.compile(r"reached required accuracy")

    toten_list: List[float] = []

    try:
        with path.open("r", errors="replace") as f:
            for line in f:
                m = toten_re.search(line)
                if m:
                    toten_list.append(float(m.group(1)))

                m = efermi_re.search(line)
                if m:
                    result["efermi"] = float(m.group(1))

                m = nelect_re.search(line)
                if m:
                    result["nelect"] = float(m.group(1))

                m = nkpts_re.search(line)
                if m:
                    result["nkpts"] = int(m.group(1))

                m = nbands_re.search(line)
                if m:
                    result["nbands"] = int(m.group(1))

                m = force_re.search(line)
                if m:
                    result["max_force"] = float(m.group(1))
                    result["rms_force"] = float(m.group(2))

                m = mag_re.search(line)
                if m:
                    result["magnetization"] = float(m.group(1))

                if converg_re.search(line):
                    result["converged"] = True

    except Exception as e:
        result["parse_error"] = str(e)

    if toten_list:
        result["toten"] = toten_list[-1]
        result["toten_history"] = toten_list

    if "converged" not in result:
        result["converged"] = False

    return result


def check_required_files(work_dir: Path) -> Dict[str, bool]:
    """Check which required VASP input files exist."""
    d = Path(work_dir)
    return {
        "INCAR":   (d / "INCAR").exists(),
        "POSCAR":  (d / "POSCAR").exists(),
        "KPOINTS": (d / "KPOINTS").exists(),
        "POTCAR":  (d / "POTCAR").exists(),
    }


def write_input_files(
    work_dir: Path,
    poscar: str,
    incar: str,
    kpoints: str,
    potcar_content: Optional[str] = None,
) -> None:
    """Write all input files to the working directory."""
    d = Path(work_dir)
    d.mkdir(parents=True, exist_ok=True)
    (d / "POSCAR").write_text(poscar)
    (d / "INCAR").write_text(incar)
    (d / "KPOINTS").write_text(kpoints)
    if potcar_content:
        (d / "POTCAR").write_text(potcar_content, errors="replace")
