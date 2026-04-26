"""KPOINTS file generation."""
from __future__ import annotations
from typing import List, Optional, Tuple


def gamma_kpoints(nx: int, ny: int, nz: int, shift: Tuple[float, float, float] = (0, 0, 0)) -> str:
    return (
        f"Gamma-centred {nx}x{ny}x{nz}\n"
        f"0\n"
        f"Gamma\n"
        f"  {nx}  {ny}  {nz}\n"
        f"  {shift[0]:.1f}  {shift[1]:.1f}  {shift[2]:.1f}\n"
    )


def mp_kpoints(nx: int, ny: int, nz: int, shift: Tuple[float, float, float] = (0, 0, 0)) -> str:
    return (
        f"Monkhorst-Pack {nx}x{ny}x{nz}\n"
        f"0\n"
        f"Monkhorst-Pack\n"
        f"  {nx}  {ny}  {nz}\n"
        f"  {shift[0]:.1f}  {shift[1]:.1f}  {shift[2]:.1f}\n"
    )


def gamma_only() -> str:
    return "Gamma-only\n0\nGamma\n  1  1  1\n  0  0  0\n"


def line_kpoints(kpoints: List[Tuple[str, Tuple[float, float, float]]], npoints: int = 20) -> str:
    """Generate line-mode KPOINTS for band structure.

    kpoints: list of (label, (kx, ky, kz)) in fractional coordinates.
    Adjacent pairs form segments.
    """
    lines = [f"k-path band structure", f"{npoints}", "Line-mode", "reciprocal"]
    for i in range(0, len(kpoints) - 1, 2):
        lbl1, k1 = kpoints[i]
        lbl2, k2 = kpoints[i + 1]
        lines.append(f"  {k1[0]:.6f}  {k1[1]:.6f}  {k1[2]:.6f}  ! {lbl1}")
        lines.append(f"  {k2[0]:.6f}  {k2[1]:.6f}  {k2[2]:.6f}  ! {lbl2}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# ─── High-symmetry k-paths ────────────────────────────────────────────────────
# Format: list of (label, (kx, ky, kz)) in reciprocal fractional coords.
# Each consecutive pair forms a k-segment.

KPATHS: dict = {
    "FCC – Simple cubic path (Γ→X→M→Γ→R→X)": [
        ("G", (0.0, 0.0, 0.0)), ("X", (0.5, 0.0, 0.5)),
        ("X", (0.5, 0.0, 0.5)), ("U", (0.625, 0.25, 0.625)),
        ("K", (0.375, 0.375, 0.75)), ("G", (0.0, 0.0, 0.0)),
        ("G", (0.0, 0.0, 0.0)), ("L", (0.5, 0.5, 0.5)),
        ("L", (0.5, 0.5, 0.5)), ("W", (0.5, 0.25, 0.75)),
        ("W", (0.5, 0.25, 0.75)), ("X", (0.5, 0.0, 0.5)),
    ],
    "BCC – Γ→H→N→Γ→P→H": [
        ("G", (0.0, 0.0, 0.0)), ("H", (0.5, -0.5, 0.5)),
        ("H", (0.5, -0.5, 0.5)), ("N", (0.0, 0.0, 0.5)),
        ("N", (0.0, 0.0, 0.5)), ("G", (0.0, 0.0, 0.0)),
        ("G", (0.0, 0.0, 0.0)), ("P", (0.25, 0.25, 0.25)),
        ("P", (0.25, 0.25, 0.25)), ("H", (0.5, -0.5, 0.5)),
    ],
    "Hexagonal – Γ→M→K→Γ→A→L→H→A": [
        ("G", (0.0, 0.0, 0.0)), ("M", (0.5, 0.0, 0.0)),
        ("M", (0.5, 0.0, 0.0)), ("K", (0.333, 0.333, 0.0)),
        ("K", (0.333, 0.333, 0.0)), ("G", (0.0, 0.0, 0.0)),
        ("G", (0.0, 0.0, 0.0)), ("A", (0.0, 0.0, 0.5)),
        ("A", (0.0, 0.0, 0.5)), ("L", (0.5, 0.0, 0.5)),
        ("L", (0.5, 0.0, 0.5)), ("H", (0.333, 0.333, 0.5)),
        ("H", (0.333, 0.333, 0.5)), ("A", (0.0, 0.0, 0.5)),
    ],
    "Tetragonal – Γ→X→M→Γ→Z→R→A→Z": [
        ("G", (0.0, 0.0, 0.0)), ("X", (0.5, 0.0, 0.0)),
        ("X", (0.5, 0.0, 0.0)), ("M", (0.5, 0.5, 0.0)),
        ("M", (0.5, 0.5, 0.0)), ("G", (0.0, 0.0, 0.0)),
        ("G", (0.0, 0.0, 0.0)), ("Z", (0.0, 0.0, 0.5)),
        ("Z", (0.0, 0.0, 0.5)), ("R", (0.5, 0.0, 0.5)),
        ("R", (0.5, 0.0, 0.5)), ("A", (0.5, 0.5, 0.5)),
        ("A", (0.5, 0.5, 0.5)), ("Z", (0.0, 0.0, 0.5)),
    ],
    "Orthorhombic – Γ→X→S→Y→Γ→Z→U→R→T→Z": [
        ("G", (0.0, 0.0, 0.0)), ("X", (0.5, 0.0, 0.0)),
        ("X", (0.5, 0.0, 0.0)), ("S", (0.5, 0.5, 0.0)),
        ("S", (0.5, 0.5, 0.0)), ("Y", (0.0, 0.5, 0.0)),
        ("Y", (0.0, 0.5, 0.0)), ("G", (0.0, 0.0, 0.0)),
        ("G", (0.0, 0.0, 0.0)), ("Z", (0.0, 0.0, 0.5)),
    ],
    "Cubic simple – Γ→X→M→Γ→R→X": [
        ("G", (0.0, 0.0, 0.0)), ("X", (0.5, 0.0, 0.0)),
        ("X", (0.5, 0.0, 0.0)), ("M", (0.5, 0.5, 0.0)),
        ("M", (0.5, 0.5, 0.0)), ("G", (0.0, 0.0, 0.0)),
        ("G", (0.0, 0.0, 0.0)), ("R", (0.5, 0.5, 0.5)),
        ("R", (0.5, 0.5, 0.5)), ("X", (0.5, 0.0, 0.0)),
    ],
    "2D Hexagonal – Γ→M→K→Γ": [
        ("G", (0.0, 0.0, 0.0)), ("M", (0.5, 0.0, 0.0)),
        ("M", (0.5, 0.0, 0.0)), ("K", (0.333, 0.333, 0.0)),
        ("K", (0.333, 0.333, 0.0)), ("G", (0.0, 0.0, 0.0)),
    ],
}


def kpath_label(kpoints: List[Tuple[str, Tuple[float, float, float]]]) -> str:
    """Return printable k-path string like Γ→X→M→Γ."""
    seen: List[str] = []
    prev = None
    for lbl, _ in kpoints:
        display = "Γ" if lbl == "G" else lbl
        if display != prev:
            seen.append(display)
        prev = display
    return "→".join(seen)
