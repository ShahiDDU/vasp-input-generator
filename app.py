"""VASP GUI — Streamlit web application."""
from __future__ import annotations
import copy
import io
import os
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

st.set_page_config(
    page_title="VASP Input Generator",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.plans import (
    IS_CLOUD, FREE_CALC_TYPES, UPGRADE_URL,
    is_pro, is_logged_in, pro_gate, upgrade_banner, setup_auth,
)
from core.incar_data import CALC_TEMPLATES, PARAM_INFO, render_incar
from core.poscar import COMMON_STRUCTURES, cif_to_poscar, get_elements, poscar_info
from core.kpoints import (
    KPATHS, gamma_kpoints, gamma_only, kpath_label, line_kpoints, mp_kpoints,
)
from core.potcar import (
    RECOMMENDED,
    assemble_potcar, get_available_variants, get_enmax,
    get_recommended_variant, suggest_encut,
)
from core.runner import (
    check_required_files, check_vasp_available, parse_outcar_summary,
    run_vasp, tail_oszicar, tail_outcar, write_input_files,
)

# ─── Auth setup (no-op locally; activates paywall on Streamlit Cloud) ─────────
_AUTH_ACTIVE = setup_auth()

# ─── Session state defaults ───────────────────────────────────────────────────
_DEFAULTS: Dict[str, Any] = {
    "step": 0,
    "poscar_text": "",
    "elements": [],
    "calc_type": "scf",
    "_prev_calc_type": "scf",
    "kpoints_type": "Gamma-centered",
    "kpoints_nx": 6, "kpoints_ny": 6, "kpoints_nz": 6,
    "kpoints_path_key": list(KPATHS.keys())[0],
    "kpoints_npoints": 20,
    "kpoints_text": gamma_kpoints(6, 6, 6),
    "potcar_functional": "PBE",
    "potcar_variants": {},
    "potcar_assembled": False,
    "potcar_content": "",
    "work_dir": str(Path.home() / "vasp_run"),
    "vasp_binary": "vasp_std",
    "vasp_np": 4,
    "vasp_omp": 1,
    "job_proc": None,
    "job_done": False,
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

ss = st.session_state

STEPS = [
    ("1", "🏗️ Crystal Structure"),
    ("2", "⚡ INCAR Parameters"),
    ("3", "📐 K-Points"),
    ("4", "🔩 POTCAR Guide"),
    ("5", "📦 Download / Run"),
    ("6", "📊 Results"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚛️ VASP Input Generator")
    st.caption("VASP 6.x compatible  ·  v1.1")
    st.divider()

    for i, (num, label) in enumerate(STEPS):
        # Hide Steps 5-6 on cloud (local execution not available)
        if IS_CLOUD and i >= 5:
            continue
        is_done    = i < ss.step
        is_current = i == ss.step
        prefix = "✅ " if is_done else ("▶ " if is_current else "   ")
        btn_style = "primary" if is_current else "secondary"
        if st.button(
            f"{prefix}{label}",
            key=f"nav_btn_{i}",
            use_container_width=True,
            type=btn_style,
        ):
            ss.step = i
            st.rerun()

    st.divider()
    max_step = 4 if IS_CLOUD else len(STEPS) - 1
    col_b, col_n = st.columns(2)
    if col_b.button("◀ Back", disabled=ss.step == 0, use_container_width=True):
        ss.step -= 1
        st.rerun()
    if col_n.button("Next ▶", disabled=ss.step >= max_step, use_container_width=True):
        ss.step += 1
        st.rerun()

    if not IS_CLOUD:
        st.divider()
        st.markdown("**VASP binaries**")
        for bname, ok in check_vasp_available().items():
            st.markdown(f"{'🟢' if ok else '🔴'} `{bname}`")

    if ss.elements:
        st.divider()
        st.markdown(f"**Elements:** `{' '.join(ss.elements)}`")
        tpl = CALC_TEMPLATES.get(ss.calc_type, {})
        st.markdown(f"**Calc:** {tpl.get('icon','')}{tpl.get('label','')}")

    # ── Pricing (cloud only) ─────────────────────────────────────────────────
    if IS_CLOUD:
        st.divider()
        if is_pro():
            st.success("✅ Pro plan active")
            email = st.session_state.get("email", "")
            if email:
                st.caption(email)
        else:
            st.markdown("### ⭐ Pro Plan")
            st.markdown(
                "- All 10+ calculation types\n"
                "- Band structure k-paths\n"
                "- ZIP download (all files)\n"
                "- POTCAR variant guide\n"
                "- Priority support"
            )
            st.markdown(f"**$9/month · $79/year**")
            st.link_button("Upgrade to Pro →", UPGRADE_URL, use_container_width=True, type="primary")


# ─────────────────────────────────────────────────────────────────────────────
# Widget helpers
# ─────────────────────────────────────────────────────────────────────────────

def _wkey(param_name: str) -> str:
    return f"w_{ss.calc_type}_{param_name}"


def _wval(param_name: str) -> Any:
    key = _wkey(param_name)
    if key in ss:
        return ss[key]
    tpl_params = CALC_TEMPLATES[ss.calc_type]["params"]
    return tpl_params.get(param_name, PARAM_INFO.get(param_name, {}).get("default", ""))


def _param_widget(name: str) -> Any:
    info   = PARAM_INFO.get(name, {})
    ptype  = info.get("type", "str")
    opts   = info.get("options")
    desc   = info.get("desc", "")
    tip    = info.get("tip", "")
    full_help = desc + ("\n\n💡 " + tip if tip else "")
    key    = _wkey(name)
    val    = _wval(name)

    if opts:
        opt_vals   = [o[0] for o in opts]
        opt_labels = [str(o[1]) for o in opts]
        try:
            idx = opt_vals.index(val)
        except ValueError:
            idx = 0
        return st.selectbox(name, opt_labels, index=idx, help=full_help, key=key,
                            format_func=lambda x: x)

    if ptype == "bool":
        bool_val = str(val).upper() in (".TRUE.", "TRUE", "T", "1", "YES")
        result = st.checkbox(name, value=bool_val, help=full_help, key=key)
        return ".TRUE." if result else ".FALSE."

    if ptype == "int":
        try:
            iv = int(val)
        except (ValueError, TypeError):
            iv = int(info.get("default", 0))
        return st.number_input(name, value=iv, step=1, help=full_help, key=key)

    if ptype == "float":
        try:
            fv = float(val)
        except (ValueError, TypeError):
            fv = float(info.get("default", 0.0))
        return st.number_input(name, value=fv, format="%.4f", help=full_help, key=key)

    return st.text_input(name, value=str(val) if val is not None else "", help=full_help, key=key)


def _selectbox_val(name: str) -> Any:
    info = PARAM_INFO.get(name, {})
    opts = info.get("options")
    raw  = ss.get(_wkey(name))
    if opts is None or raw is None:
        return raw
    opt_vals   = [o[0] for o in opts]
    opt_labels = [str(o[1]) for o in opts]
    if raw in opt_labels:
        return opt_vals[opt_labels.index(raw)]
    if raw in opt_vals:
        return raw
    return opt_vals[0]


def _collect_params() -> Dict[str, Any]:
    tpl    = CALC_TEMPLATES[ss.calc_type]
    result = {}
    result["SYSTEM"] = ss.get(_wkey("SYSTEM"), tpl["params"].get("SYSTEM", "VASP"))
    for name in tpl["params"]:
        if name == "SYSTEM":
            continue
        info = PARAM_INFO.get(name, {})
        if info.get("options"):
            result[name] = _selectbox_val(name)
        else:
            result[name] = ss.get(_wkey(name), tpl["params"][name])
    for extra in ["IVDW", "NCORE", "KPAR", "METAGGA", "CMBJ", "LASPH",
                  "ISPIN", "MAGMOM", "LSORBIT", "LNONCOLLINEAR",
                  "LDAU", "LDAUTYPE", "LDAUL", "LDAUU", "LDAUJ",
                  "LHFCALC", "AEXX", "HFSCREEN", "LVTOT", "LVHAR",
                  "EMIN", "EMAX", "NEDOS"]:
        k = _wkey(extra)
        if k in ss:
            info = PARAM_INFO.get(extra, {})
            if info.get("options"):
                result[extra] = _selectbox_val(extra)
            else:
                result[extra] = ss[k]
    return {k: v for k, v in result.items() if v != "" and v is not None}


def _build_zip() -> bytes:
    """Return INCAR + POSCAR + KPOINTS packed as a ZIP."""
    params_dict = _collect_params()
    incar_text  = render_incar(params_dict)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("INCAR",   incar_text)
        zf.writestr("POSCAR",  ss.poscar_text)
        zf.writestr("KPOINTS", ss.kpoints_text)
        if ss.potcar_assembled and ss.potcar_content:
            zf.writestr("POTCAR", ss.potcar_content)
    return buf.getvalue()


# ═════════════════════════════════════════════════════════════════════════════
# STEP 0 — Crystal Structure
# ═════════════════════════════════════════════════════════════════════════════
def step_structure():
    st.header("Step 1 · Crystal Structure (POSCAR)")
    st.markdown(
        "Provide the crystal structure. Upload a **POSCAR** or **CIF** file, "
        "choose a preset, or paste/edit the POSCAR manually."
    )

    tab_upload, tab_cif, tab_preset, tab_manual = st.tabs([
        "📂 Upload file", "🔬 Paste CIF", "🏗️ Presets", "✏️ Manual",
    ])

    with tab_upload:
        f = st.file_uploader("Upload POSCAR or CIF", type=["poscar","cif","vasp","txt",""])
        if f:
            raw = f.read()
            if f.name.lower().endswith(".cif"):
                try:
                    ss.poscar_text = cif_to_poscar(raw)
                    _refresh_elements()
                    st.success("CIF converted to POSCAR.")
                except Exception as e:
                    st.error(f"CIF conversion failed: {e}")
            else:
                ss.poscar_text = raw.decode("utf-8", errors="replace")
                _refresh_elements()
                st.success("POSCAR loaded.")

    with tab_cif:
        cif_txt = st.text_area("Paste CIF content here", height=220, key="cif_area")
        prim    = st.checkbox("Use primitive cell", value=False)
        if st.button("Convert CIF → POSCAR"):
            if cif_txt.strip():
                try:
                    ss.poscar_text = cif_to_poscar(cif_txt.encode(), primitive=prim)
                    _refresh_elements()
                    st.success("Conversion successful.")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Paste CIF content first.")

    with tab_preset:
        preset = st.selectbox("Choose a preset", list(COMMON_STRUCTURES.keys()))
        col1, col2 = st.columns([1, 3])
        if col1.button("Load Preset", type="primary"):
            ss.poscar_text = COMMON_STRUCTURES[preset]["poscar"]
            _refresh_elements()
            st.success(f"Loaded: {preset}")
        info_p = poscar_info(COMMON_STRUCTURES[preset]["poscar"])
        if "error" not in info_p:
            col2.info(
                f"Formula: **{info_p['formula']}** | {info_p['n_atoms']} atoms | "
                f"a={info_p['a']:.3f} Å, b={info_p['b']:.3f} Å, c={info_p['c']:.3f} Å"
            )

    with tab_manual:
        edited = st.text_area("Edit POSCAR", value=ss.poscar_text, height=300, key="poscar_manual")
        if st.button("Apply"):
            ss.poscar_text = edited
            _refresh_elements()

    st.divider()
    if ss.poscar_text.strip():
        info = poscar_info(ss.poscar_text)
        if "error" in info:
            st.error(f"POSCAR parse error: {info['error']}")
        else:
            st.subheader("Structure Summary")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Formula",     info["formula"])
            c2.metric("N atoms",     info["n_atoms"])
            c3.metric("Volume (Å³)", f"{info['volume']:.3f}")
            c4.metric("Elements",    ", ".join(info["elements"]) or "—")

            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("a (Å)", f"{info['a']:.4f}")
            c2.metric("b (Å)", f"{info['b']:.4f}")
            c3.metric("c (Å)", f"{info['c']:.4f}")
            c4.metric("α (°)", f"{info['alpha']:.2f}")
            c5.metric("β (°)", f"{info['beta']:.2f}")
            c6.metric("γ (°)", f"{info['gamma']:.2f}")

            with st.expander("POSCAR file content"):
                st.code(ss.poscar_text, language="text")

        if not ss.elements:
            st.warning(
                "⚠️ Species names not detected in line 6 of POSCAR. "
                "Make sure your POSCAR has element symbols before the atom counts."
            )
    else:
        st.info("No structure loaded yet — use one of the tabs above.")


def _refresh_elements():
    ss.elements = get_elements(ss.poscar_text)
    ss.potcar_variants  = {}
    ss.potcar_assembled = False
    ss.potcar_content   = ""


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — INCAR
# ═════════════════════════════════════════════════════════════════════════════
def step_incar():
    st.header("Step 2 · INCAR Parameters")

    # ── Calculation type selector ─────────────────────────────────────────────
    calc_labels = {k: f"{v['icon']} {v['label']}" for k, v in CALC_TEMPLATES.items()}

    # Free tier: SCF only
    if IS_CLOUD and not is_pro():
        upgrade_banner()
        available_keys = [k for k in CALC_TEMPLATES if k in FREE_CALC_TYPES]
        st.info(
            "⭐ **Free plan**: SCF (self-consistent field) is included. "
            f"[Upgrade to Pro]({UPGRADE_URL}) to unlock relaxation, band structure, "
            "HSE06, SOC, DFT+U, MD, and more."
        )
    else:
        available_keys = list(CALC_TEMPLATES.keys())

    available_labels = [calc_labels[k] for k in available_keys]
    current_idx = available_keys.index(ss.calc_type) if ss.calc_type in available_keys else 0

    chosen_label = st.selectbox(
        "Calculation type",
        available_labels,
        index=current_idx,
        key="calc_type_sel",
        help="Choosing a new type resets all parameters to the recommended defaults for that workflow.",
    )
    new_type = available_keys[available_labels.index(chosen_label)]

    if new_type != ss.calc_type:
        ss.calc_type       = new_type
        ss._prev_calc_type = new_type
        st.rerun()

    tpl = CALC_TEMPLATES[ss.calc_type]
    st.info(f"{tpl['icon']} **{tpl['label']}** — {tpl['desc']}")

    bin_needed = tpl.get("vasp_bin", "vasp_std")
    if bin_needed != "vasp_std" and not IS_CLOUD:
        st.warning(f"⚠️ This calculation requires **{bin_needed}**. "
                   "The correct binary will be pre-selected in Step 5.")

    st.divider()

    ss[_wkey("SYSTEM")] = st.text_input(
        "SYSTEM (label for OUTCAR)",
        value=_wval("SYSTEM"),
        key=_wkey("SYSTEM") + "_widget",
        help="Free-text description written into OUTCAR. Helps identify runs.",
    )

    with st.expander("⚡ Electronic Settings", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            for p in ["ISTART", "ICHARG", "ENCUT", "EDIFF"]:
                if p in tpl["params"]:
                    _param_widget(p)
        with c2:
            for p in ["PREC", "ALGO", "NELM", "NELMIN"]:
                if p in tpl["params"]:
                    _param_widget(p)

        algo_val = _wval("ALGO")
        if algo_val in ("Fast", "VeryFast"):
            st.warning(
                "💡 **ALGO=Fast/VeryFast**: RMM-DIIS can diverge for insulators and "
                "magnetic systems. If you see oscillating energy, switch to **Normal**."
            )
        if ss.calc_type in ("mbj", "r2scan", "hse06"):
            st.info(
                "💡 **ALGO=All** is required for meta-GGA (mBJ, R2SCAN) and hybrid (HSE06) "
                "functionals. It is pre-set here."
            )

    with st.expander("🌡️ Smearing", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            if "ISMEAR" in tpl["params"]:
                _param_widget("ISMEAR")
        with c2:
            if "SIGMA" in tpl["params"]:
                _param_widget("SIGMA")

        ismear = _wval("ISMEAR")
        try:
            ismear = int(ismear) if isinstance(ismear, str) else ismear
        except Exception:
            ismear = 0
        if ismear == -5:
            st.info(
                "💡 **ISMEAR=-5 (Tetrahedron)**: Most accurate for insulators and DOS. "
                "Requires ≥3 k-points in each direction. **Do NOT use for relaxation or metals.**"
            )
        elif ismear == 0:
            st.info(
                "💡 **ISMEAR=0 (Gaussian)**: Safe general-purpose choice. "
                "Good for semiconductors and band structure. Keep SIGMA ≤ 0.1 eV."
            )
        elif isinstance(ismear, int) and ismear >= 1:
            st.info(
                f"💡 **ISMEAR={ismear} (Methfessel-Paxton)**: Good for metals. "
                "Use SIGMA=0.1–0.2 eV. Check that T×S entropy < 1 meV/atom in OUTCAR."
            )

    show_metagga = ss.calc_type in ("mbj", "r2scan") or "METAGGA" in tpl["params"]
    with st.expander("🔬 Meta-GGA Settings", expanded=show_metagga):
        _param_widget("METAGGA")
        metagga_val = _wval("METAGGA")
        if isinstance(metagga_val, str) and metagga_val:
            _param_widget("LASPH")
            st.success(
                "💡 **LASPH=.TRUE.** is required for all meta-GGA functionals. "
                "It includes non-spherical contributions to the PAW one-centre terms."
            )
            if metagga_val == "MBJ":
                _param_widget("CMBJ")
                st.warning(
                    "⚠️ **mBJ note**: This functional gives excellent band gaps but "
                    "**no reliable total energy or forces**. Use it only for electronic "
                    "structure analysis after relaxing the geometry with PBE."
                )
            elif metagga_val in ("R2SCAN", "SCAN"):
                st.info(
                    "💡 **R2SCAN/SCAN**: More accurate than PBE for structures and "
                    "energetics. Expect ~3–5× more iterations than PBE."
                )
        else:
            st.caption("Select a meta-GGA functional above to see options.")

    with st.expander("🧲 Spin & Magnetism"):
        c1, c2 = st.columns(2)
        with c1:
            _param_widget("ISPIN")
            if _wval("ISPIN") == 2 or _wval("ISPIN") == "2":
                _param_widget("MAGMOM")
                st.info(
                    "💡 **MAGMOM**: Set initial moments to break symmetry. "
                    f"Elements: `{' '.join(ss.elements) or '(load structure first)'}`. "
                    "Typical: Fe≈4, Co≈3, Ni≈2, Mn≈5 μB."
                )
        with c2:
            _param_widget("LSORBIT")
            if _wval("LSORBIT") in (".TRUE.", True):
                _param_widget("LNONCOLLINEAR")
                st.warning(
                    "⚠️ **SOC** requires **vasp_ncl** binary. "
                    "Start from a scalar-relativistic CHGCAR (ICHARG=11)."
                )

    ionic_keys = ["IBRION", "NSW", "EDIFFG", "ISIF", "POTIM", "ISYM"]
    if any(k in tpl["params"] for k in ionic_keys):
        with st.expander("🔄 Ionic / Relaxation", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                for p in ["IBRION", "NSW", "EDIFFG"]:
                    if p in tpl["params"]:
                        _param_widget(p)
            with c2:
                for p in ["ISIF", "POTIM", "ISYM"]:
                    if p in tpl["params"]:
                        _param_widget(p)

            ediffg_v = _wval("EDIFFG")
            try:
                ediffg_f = float(str(ediffg_v))
                if ediffg_f > 0:
                    st.info(
                        "💡 Positive EDIFFG = energy threshold (eV). "
                        "Negative is preferred — it means max force in eV/Å."
                    )
                elif ediffg_f > -0.005:
                    st.info(
                        "💡 EDIFFG < -0.005 eV/Å is very tight. "
                        "Use -0.001 for phonon pre-relaxation, -0.02 for general use."
                    )
            except (ValueError, TypeError):
                pass

    if ss.calc_type == "md_nvt":
        with st.expander("🌡️ Molecular Dynamics", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                for p in ["MDALGO", "TEBEG", "TEEND"]:
                    _param_widget(p)
            with c2:
                for p in ["POTIM", "NSW", "SMASS"]:
                    _param_widget(p)
            st.info(
                "💡 **MD tips**: POTIM=2 fs is standard. Use POTIM=1 fs for H-containing systems. "
                "Run ≥500 steps for equilibration before collecting statistics."
            )

    if ss.calc_type == "dos":
        with st.expander("📊 DOS Energy Range", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1: _param_widget("EMIN")
            with c2: _param_widget("EMAX")
            with c3: _param_widget("NEDOS")
            st.info(
                "💡 Set EMIN and EMAX relative to the Fermi level from your SCF OUTCAR. "
                "Use NEDOS ≥ 2000 for smooth publication-quality plots."
            )

    show_dftu = ss.calc_type == "dftu" or "LDAU" in tpl["params"]
    with st.expander("🧲 DFT+U Settings", expanded=show_dftu):
        _param_widget("LDAU")
        ldau_v = _wval("LDAU")
        if ldau_v in (".TRUE.", True, "True"):
            c1, c2 = st.columns(2)
            with c1:
                _param_widget("LDAUTYPE")
                _param_widget("LASPH")
            with c2:
                _param_widget("LDAUL")
                _param_widget("LDAUU")
                _param_widget("LDAUJ")
            st.info(
                f"💡 **DFT+U order**: species order matches POSCAR line 6: "
                f"`{' '.join(ss.elements) or '(load structure first)'}`. "
                "Example for Fe₂O₃ with U=4 on Fe: LDAUL=2 -1, LDAUU=4.0 0.0, LDAUJ=0 0."
            )
        else:
            st.caption("Enable LDAU above to configure Hubbard U parameters.")

    show_hf = ss.calc_type == "hse06" or "LHFCALC" in tpl["params"]
    with st.expander("💎 Hybrid Functional", expanded=show_hf):
        _param_widget("LHFCALC")
        if _wval("LHFCALC") in (".TRUE.", True):
            c1, c2 = st.columns(2)
            with c1: _param_widget("AEXX")
            with c2: _param_widget("HFSCREEN")
            st.info(
                "💡 **HSE06 = AEXX=0.25, HFSCREEN=0.2**. "
                "**PBE0 = AEXX=0.25, HFSCREEN=0** (unscreened, expensive for metals). "
                "Start from a PBE WAVECAR (ISTART=1, ICHARG=1) to accelerate convergence."
            )

    with st.expander("🌐 van der Waals Correction"):
        _param_widget("IVDW")
        ivdw_v = _wval("IVDW")
        ivdw_i = int(ivdw_v) if str(ivdw_v).lstrip("-").isdigit() else 0
        if ivdw_i == 12:
            st.info(
                "💡 **DFT-D3/BJ** (IVDW=12) is the recommended vdW correction for most systems: "
                "layered materials, molecular crystals, adsorption on surfaces."
            )
        elif ivdw_i == 202:
            st.info(
                "💡 **MBD** (IVDW=202) is the most accurate dispersion scheme but ~3× slower. "
                "Recommended for large unit cells or when pairwise D3 is insufficient."
            )

    with st.expander("📁 Output Control"):
        c1, c2, c3 = st.columns(3)
        with c1:
            _param_widget("LORBIT")
            st.caption("LORBIT=11 → lm-decomposed PDOS + PROCAR (recommended)")
        with c2:
            _param_widget("LWAVE")
            _param_widget("LVTOT")
        with c3:
            _param_widget("LCHARG")
            _param_widget("LVHAR")

    with st.expander("⚙️ Parallelisation"):
        c1, c2 = st.columns(2)
        with c1:
            _param_widget("NCORE")
        with c2:
            _param_widget("KPAR")
        ncore_v = ss.get(_wkey("NCORE"), 4)
        kpar_v  = ss.get(_wkey("KPAR"),  1)
        try:
            total = int(ncore_v) * int(kpar_v)
            st.info(
                f"💡 NCORE × KPAR = **{total}** total MPI processes per node group. "
                "Set NCORE ≈ √(MPI processes per k-group). "
                "Example: 64 MPI, KPAR=2 → 32 per group → NCORE=4 or 8."
            )
        except Exception:
            pass

    st.divider()
    st.subheader("INCAR Preview")
    params_dict = _collect_params()
    incar_text  = render_incar(params_dict)
    st.code(incar_text, language="text")
    st.download_button("⬇️ Download INCAR", incar_text, file_name="INCAR", mime="text/plain")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — KPOINTS
# ═════════════════════════════════════════════════════════════════════════════
def step_kpoints():
    st.header("Step 3 · K-Points (KPOINTS)")
    st.markdown("Choose the Brillouin zone sampling strategy.")

    if IS_CLOUD and not is_pro():
        ktype_opts = ["Gamma-centered", "Monkhorst-Pack", "Gamma-only (Γ)", "Manual"]
        st.info(
            f"⭐ **Line-mode** (band structure k-paths) requires Pro. "
            f"[Upgrade →]({UPGRADE_URL})"
        )
    else:
        ktype_opts = [
            "Gamma-centered",
            "Monkhorst-Pack",
            "Gamma-only (Γ)",
            "Line-mode (band structure)",
            "Manual",
        ]

    if ss.kpoints_type not in ktype_opts:
        ss.kpoints_type = ktype_opts[0]

    ktype = st.radio("K-point type", ktype_opts,
                     index=ktype_opts.index(ss.kpoints_type),
                     horizontal=True, key="ktype_radio")
    ss.kpoints_type = ktype

    st.divider()

    if ktype in ("Gamma-centered", "Monkhorst-Pack"):
        st.markdown(
            "**Suggested meshes:** 4×4×4 (coarse, metals), 6×6×6 (standard), "
            "8×8×8 (accurate), 12×12×12 (high-precision). For 2D slabs: set **nz=1**."
        )
        c1, c2, c3 = st.columns(3)
        nx = c1.number_input("nx", 1, 30, ss.kpoints_nx, key="kp_nx")
        ny = c2.number_input("ny", 1, 30, ss.kpoints_ny, key="kp_ny")
        nz = c3.number_input("nz", 1, 30, ss.kpoints_nz, key="kp_nz")
        ss.kpoints_nx, ss.kpoints_ny, ss.kpoints_nz = int(nx), int(ny), int(nz)

        if ktype == "Gamma-centered":
            ss.kpoints_text = gamma_kpoints(ss.kpoints_nx, ss.kpoints_ny, ss.kpoints_nz)
            st.info(
                "💡 **Gamma-centered** is the standard choice for most calculations. "
                "Always includes the Γ point, which is required for optical and phonon calculations."
            )
        else:
            ss.kpoints_text = mp_kpoints(ss.kpoints_nx, ss.kpoints_ny, ss.kpoints_nz)
            st.info(
                "💡 **Monkhorst-Pack** (MP) avoids the Γ point. "
                "Often equivalent to Gamma-centered for large meshes. "
                "Use Gamma-centered if in doubt."
            )

    elif ktype == "Gamma-only (Γ)":
        ss.kpoints_text = gamma_only()
        st.info(
            "💡 **Single Γ-point**: Use for large supercells (≥ ~50 atoms), "
            "molecules in a box, or quick pre-tests. "
            "Not suitable for band structure or accurate DOS."
        )

    elif ktype == "Line-mode (band structure)":
        st.markdown(
            "Select a high-symmetry k-path for your crystal system. "
            "**Prerequisites**: Run an SCF calculation first and have **CHGCAR** in the working directory."
        )
        path_keys = list(KPATHS.keys())
        path_key  = st.selectbox(
            "Crystal system / k-path",
            path_keys,
            index=path_keys.index(ss.kpoints_path_key) if ss.kpoints_path_key in path_keys else 0,
            key="kpath_sel",
        )
        ss.kpoints_path_key = path_key
        kpath = KPATHS[path_key]

        npts = st.slider("K-points per segment", 10, 80, ss.kpoints_npoints, 5, key="kpts_slider")
        ss.kpoints_npoints = npts

        st.success(f"**Path:** {kpath_label(kpath)}  ({npts} pts/segment)")
        st.info(
            "💡 20–30 points per segment is sufficient for plotting. "
            "The path uses fractional reciprocal coordinates."
        )
        ss.kpoints_text = line_kpoints(kpath, npts)

        with st.expander("K-point list"):
            rows = [{"Label": lbl, "kx": f"{k[0]:.4f}", "ky": f"{k[1]:.4f}", "kz": f"{k[2]:.4f}"}
                    for lbl, k in kpath]
            st.table(rows)

    else:  # Manual
        manual = st.text_area("KPOINTS content", value=ss.kpoints_text, height=220, key="kp_manual")
        ss.kpoints_text = manual

    st.divider()
    st.subheader("KPOINTS Preview")
    st.code(ss.kpoints_text, language="text")
    st.download_button("⬇️ Download KPOINTS", ss.kpoints_text, file_name="KPOINTS", mime="text/plain")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 — POTCAR
# ═════════════════════════════════════════════════════════════════════════════
def step_potcar():
    st.header("Step 4 · POTCAR Guide")

    if IS_CLOUD:
        _step_potcar_cloud()
    else:
        _step_potcar_local()


def _step_potcar_cloud():
    """Cloud version: recommend variants without reading proprietary files."""
    st.markdown(
        "POTCAR files are **proprietary to VASP** and cannot be distributed here. "
        "Based on your structure, we recommend the following variants:"
    )

    if not ss.elements:
        st.warning("Load a structure first (Step 1) to see POTCAR recommendations.")
        return

    if IS_CLOUD and not is_pro():
        upgrade_banner()
        st.info(
            f"⭐ POTCAR variant recommendations require Pro. "
            f"[Upgrade →]({UPGRADE_URL})"
        )
        return

    functional = st.radio(
        "Functional", ["PBE", "LDA"], horizontal=True,
        index=0 if ss.potcar_functional == "PBE" else 1,
        key="potcar_func_cloud",
    )
    ss.potcar_functional = functional

    st.markdown(f"**Elements from POSCAR:** `{' '.join(ss.elements)}`")
    st.divider()

    rows = []
    for elem in ss.elements:
        rec = RECOMMENDED.get(elem, elem)
        rows.append({"Element": elem, "Recommended variant": rec, "Functional": functional})

    st.table(rows)

    st.info(
        "💡 **How to assemble POTCAR locally:**\n"
        "```bash\n"
        "cat  $VASP_PSP_DIR/" + functional + "/{" +
        ",".join(RECOMMENDED.get(e, e) for e in ss.elements) +
        "}/POTCAR  > POTCAR\n"
        "```\n"
        "Replace `$VASP_PSP_DIR` with your local pseudopotential directory."
    )

    st.markdown("**ENCUT recommendation:** 1.3 × max(ENMAX) from the selected POTCARs.")
    st.warning(
        "⚠️ POTCAR files can only be obtained from your institution's VASP license. "
        "See the [VASP wiki](https://www.vasp.at/wiki/index.php/POTCAR) for details."
    )


def _step_potcar_local():
    """Local version: full POTCAR assembly with local files."""
    st.markdown(
        "Select the exchange-correlation functional and pseudopotential variant for each element. "
        "Recommended variants are pre-selected and ENCUT is suggested automatically."
    )

    if not ss.elements:
        st.warning("No elements detected. Go back to **Step 1** and load a structure with species names.")
        return

    functional = st.radio(
        "Exchange-correlation functional",
        ["PBE", "LDA"], horizontal=True,
        index=0 if ss.potcar_functional == "PBE" else 1,
        key="potcar_func_radio",
        help=(
            "PBE (GGA-PBE): most widely used, slight overbinding of bonds. "
            "LDA: tends to underbind and underestimate lattice constants. "
            "Use PBE for most calculations."
        ),
    )
    ss.potcar_functional = functional

    if functional == "PBE":
        st.info("💡 **PBE** is the standard choice for most calculations in materials science.")
    else:
        st.warning("💡 **LDA** overbinds structures. Only choose if you specifically need LDA for your study.")

    st.markdown(f"**Elements from POSCAR:** `{' '.join(ss.elements)}`")
    st.divider()

    variants: Dict[str, str] = {}
    all_ok = True
    enmax_vals = []

    for elem in ss.elements:
        avail = get_available_variants(elem, functional)
        if not avail:
            st.error(f"❌ No POTCAR found for **{elem}** ({functional}). Check POTCAR directory.")
            all_ok = False
            variants[elem] = elem
            continue

        rec = get_recommended_variant(elem, functional)
        default_idx = avail.index(rec) if rec and rec in avail else 0

        with st.container():
            c1, c2, c3 = st.columns([1, 2, 3])
            c1.markdown(f"**{elem}**")
            chosen = c2.selectbox(
                "Variant",
                avail, index=default_idx,
                key=f"pv_{elem}_{functional}",
                label_visibility="collapsed",
                help=(
                    "_pv = semi-core p electrons in valence (recommended for 4th row+ metals)\n"
                    "_sv = semi-core s+p electrons (most complete, most expensive)\n"
                    "_d  = d-electrons in valence (for Ga, In, Tl, Ge, Sn, Pb...)\n"
                    "No suffix = standard (usually sufficient for light elements)"
                ),
            )
            variants[elem] = chosen

            en = get_enmax(elem, chosen, functional)
            if en:
                enmax_vals.append(en)
                c3.caption(f"ENMAX = {en:.1f} eV  |  1.3× = {1.3*en:.0f} eV")

    ss.potcar_variants = variants

    if enmax_vals:
        suggested = round(1.3 * max(enmax_vals), 0)
        st.divider()
        st.success(
            f"💡 **Recommended ENCUT = {suggested:.0f} eV** "
            f"(= 1.3 × max ENMAX = 1.3 × {max(enmax_vals):.1f} eV). "
            "Using a lower ENCUT gives unconverged results; using a much higher value wastes time."
        )
        if st.button(f"✅ Apply ENCUT = {suggested:.0f} eV to INCAR"):
            ss[_wkey("ENCUT")] = suggested
            st.success(f"ENCUT set to {suggested:.0f} eV. Go to Step 2 to verify.")

    st.divider()
    if all_ok:
        if st.button("🔧 Assemble POTCAR", type="primary"):
            try:
                content = assemble_potcar(ss.elements, variants, functional)
                ss.potcar_content   = content
                ss.potcar_assembled = True
                st.success(
                    f"✅ POTCAR assembled — {len(ss.elements)} species, "
                    f"{len(content)//1024} KB."
                )
            except Exception as e:
                st.error(f"POTCAR assembly failed: {e}")
    else:
        st.error("Fix missing POTCARs before assembling.")

    if ss.potcar_assembled:
        st.success("✅ POTCAR is ready for Step 5.")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 4 — Download / Run
# ═════════════════════════════════════════════════════════════════════════════
def step_review_run():
    if IS_CLOUD:
        _step_download_cloud()
    else:
        _step_run_local()


def _step_download_cloud():
    st.header("Step 5 · Download Input Files")

    params_dict = _collect_params()
    incar_text  = render_incar(params_dict)

    checks = {
        "Structure (POSCAR)": bool(ss.poscar_text.strip()),
        "INCAR parameters":   True,
        "KPOINTS":            bool(ss.kpoints_text.strip()),
    }
    all_ready = all(checks.values())

    st.subheader("Checklist")
    for item, ok in checks.items():
        st.markdown(f"{'✅' if ok else '❌'} {item}")

    st.divider()
    st.subheader("Preview")
    tab_i, tab_p, tab_k = st.tabs(["INCAR", "POSCAR", "KPOINTS"])
    with tab_i:
        st.code(incar_text, language="text")
    with tab_p:
        st.code(ss.poscar_text or "(empty)", language="text")
    with tab_k:
        st.code(ss.kpoints_text, language="text")

    st.divider()
    st.subheader("Download")

    col1, col2, col3, col4 = st.columns(4)
    col1.download_button("⬇️ INCAR",   incar_text,       "INCAR",   disabled=not incar_text)
    col2.download_button("⬇️ POSCAR",  ss.poscar_text,   "POSCAR",  disabled=not ss.poscar_text.strip())
    col3.download_button("⬇️ KPOINTS", ss.kpoints_text,  "KPOINTS", disabled=not ss.kpoints_text.strip())

    # ZIP download — Pro only
    if is_pro():
        zip_bytes = _build_zip() if all_ready else None
        col4.download_button(
            "⬇️ All as ZIP",
            zip_bytes or b"",
            "vasp_inputs.zip",
            mime="application/zip",
            disabled=not all_ready,
            help="Downloads INCAR + POSCAR + KPOINTS in one zip file.",
        )
    else:
        col4.markdown(f"[⭐ ZIP (Pro)]({UPGRADE_URL})")

    st.divider()
    st.subheader("Next: Run VASP on your cluster")
    st.markdown(
        """
1. Download the files above and copy them to your HPC cluster.
2. Assemble **POTCAR** using the recommendations from Step 4.
3. Submit the job. Example SLURM script:

```bash
#!/bin/bash
#SBATCH --job-name=vasp_run
#SBATCH --nodes=1
#SBATCH --ntasks=32
#SBATCH --time=02:00:00

module load vasp/6.5.1
mpirun -np 32 vasp_std > vasp.log 2>&1
```
"""
    )


def _step_run_local():
    st.header("Step 5 · Review & Run")

    checks = {
        "Structure (POSCAR)": bool(ss.poscar_text.strip()),
        "INCAR parameters":   True,
        "KPOINTS":            bool(ss.kpoints_text.strip()),
        "POTCAR":             ss.potcar_assembled,
    }
    all_ready = all(checks.values())

    st.subheader("Checklist")
    for item, ok in checks.items():
        st.markdown(f"{'✅' if ok else '❌'} {item}")
    if not all_ready:
        st.warning("Complete all previous steps before running.")

    st.divider()
    st.subheader("Input Files")

    params_dict = _collect_params()
    incar_text  = render_incar(params_dict)

    tab_i, tab_p, tab_k, tab_pot = st.tabs(["INCAR", "POSCAR", "KPOINTS", "POTCAR (head)"])
    with tab_i:
        st.code(incar_text, language="text")
        st.download_button("⬇️ INCAR", incar_text, "INCAR")
    with tab_p:
        st.code(ss.poscar_text, language="text")
        st.download_button("⬇️ POSCAR", ss.poscar_text, "POSCAR")
    with tab_k:
        st.code(ss.kpoints_text, language="text")
        st.download_button("⬇️ KPOINTS", ss.kpoints_text, "KPOINTS")
    with tab_pot:
        if ss.potcar_assembled and ss.potcar_content:
            st.code(ss.potcar_content[:3000] + "\n... (truncated)", language="text")
        else:
            st.info("POTCAR not assembled yet (Step 4).")

    if all_ready:
        st.divider()
        zip_bytes = _build_zip()
        st.download_button(
            "⬇️ Download All as ZIP",
            zip_bytes, "vasp_inputs.zip",
            mime="application/zip",
            type="primary",
        )

    st.divider()
    st.subheader("Job Settings")
    c1, c2 = st.columns(2)
    with c1:
        wd = st.text_input("Working directory", value=ss.work_dir, key="wd_input")
        ss.work_dir = wd

        default_bin = CALC_TEMPLATES[ss.calc_type].get("vasp_bin", "vasp_std")
        avail_bins  = list(check_vasp_available().keys())
        if default_bin not in avail_bins:
            default_bin = avail_bins[0]
        binary = st.selectbox(
            "VASP binary",
            avail_bins,
            index=avail_bins.index(default_bin),
            key="binary_sel",
            help="vasp_std: standard | vasp_gam: Gamma-only (2× faster) | vasp_ncl: non-collinear/SOC",
        )
        ss.vasp_binary = binary

    with c2:
        np_v  = st.number_input("MPI processes", 1, 512, ss.vasp_np, key="np_input")
        omp_v = st.number_input("OMP threads", 1, 64, ss.vasp_omp, key="omp_input")
        ss.vasp_np, ss.vasp_omp = int(np_v), int(omp_v)
        st.metric("Total cores", ss.vasp_np * ss.vasp_omp)
        st.info(
            f"💡 NCORE in INCAR = {ss.get(_wkey('NCORE'), 4)}. "
            f"Ideal: NCORE × KPAR = {ss.vasp_np}. "
            "Adjust NCORE in Step 2 to match."
        )

    with st.expander("🔧 Copy WAVECAR / CHGCAR from previous run"):
        src = st.text_input("Source directory (previous SCF)", key="src_dir")
        if st.button("Copy files") and src:
            import shutil
            dst = Path(ss.work_dir)
            dst.mkdir(parents=True, exist_ok=True)
            copied = []
            for fn in ["CHGCAR", "WAVECAR"]:
                s = Path(src) / fn
                if s.exists():
                    shutil.copy2(s, dst / fn)
                    copied.append(fn)
            st.success(f"Copied: {', '.join(copied) or 'nothing found'}.")

    st.divider()
    col_w, col_r, col_s = st.columns([1, 1, 1])

    if col_w.button("📝 Write Input Files", type="secondary", disabled=not all_ready):
        try:
            write_input_files(
                Path(ss.work_dir), ss.poscar_text, incar_text, ss.kpoints_text,
                ss.potcar_content if ss.potcar_assembled else None,
            )
            st.success(f"Files written to `{ss.work_dir}`")
            for fn, ok in check_required_files(Path(ss.work_dir)).items():
                st.markdown(f"{'✅' if ok else '❌'} {fn}")
        except Exception as e:
            st.error(f"Write error: {e}")

    if col_r.button("▶ Run VASP", type="primary", disabled=not all_ready or ss.job_proc is not None):
        try:
            write_input_files(
                Path(ss.work_dir), ss.poscar_text, incar_text, ss.kpoints_text,
                ss.potcar_content if ss.potcar_assembled else None,
            )
            proc = run_vasp(Path(ss.work_dir), ss.vasp_binary, ss.vasp_np, ss.vasp_omp)
            ss.job_proc = proc
            ss.job_done = False
            st.success(f"VASP started (PID {proc.pid})")
        except Exception as e:
            st.error(f"Failed: {e}")

    if col_s.button("⏹ Stop", disabled=ss.job_proc is None):
        if ss.job_proc:
            ss.job_proc.terminate()
            ss.job_proc = None
            ss.job_done = True
            st.warning("Job terminated.")

    if ss.job_proc is not None:
        st.subheader("Live Output")
        if ss.job_proc.poll() is not None:
            ss.job_done = True
            ss.job_proc = None
            st.success("✅ Job finished! Go to Step 6 for results.")
        else:
            st.info(f"🔄 Running (PID {ss.job_proc.pid}) — page auto-refreshes every 3 s")
        lines = tail_oszicar(Path(ss.work_dir))
        if lines:
            st.code("\n".join(lines), language="text")
        else:
            st.caption("Waiting for OSZICAR…")
        if not ss.job_done:
            time.sleep(3)
            st.rerun()

    elif ss.job_done:
        st.success("Job finished. Go to **Step 6** to view results.")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 5 — Results (local only)
# ═════════════════════════════════════════════════════════════════════════════
def step_results():
    st.header("Step 6 · Results")

    rdir = st.text_input("Results directory", value=ss.work_dir, key="res_dir")
    work = Path(rdir)
    if not work.exists():
        st.warning("Directory does not exist.")
        return

    outfiles = ["OUTCAR", "OSZICAR", "vasprun.xml", "CONTCAR", "DOSCAR", "PROCAR", "CHGCAR", "WAVECAR"]
    st.subheader("Output Files")
    cols = st.columns(4)
    for i, fn in enumerate(outfiles):
        cols[i % 4].markdown(f"{'✅' if (work/fn).exists() else '⬜'} `{fn}`")

    st.divider()
    if st.button("🔍 Parse OUTCAR", type="primary"):
        res = parse_outcar_summary(work)
        if not res:
            st.warning("No results found — is OUTCAR present?")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Energy (eV)", f"{res['toten']:.6f}" if "toten" in res else "—")
            c2.metric("E-Fermi (eV)",      f"{res['efermi']:.4f}" if "efermi" in res else "—")
            c3.metric("NKPTS",             res.get("nkpts", "—"))
            c4.metric("NBANDS",            res.get("nbands", "—"))

            if res.get("converged"):
                st.success("✅ Calculation converged.")
            else:
                st.error("❌ Not converged. Try: increase NELM, change ALGO, reduce POTIM, check structure.")

            if "max_force" in res:
                fval = res["max_force"]
                label = "Max Force (eV/Å)"
                if fval < 0.02:
                    st.metric(label, f"{fval:.4f}", delta="✅ converged")
                else:
                    st.metric(label, f"{fval:.4f}", delta="⚠️ not converged", delta_color="inverse")

            if "magnetization" in res:
                st.metric("Magnetization (μB)", f"{res['magnetization']:.3f}")

            if "toten_history" in res and len(res["toten_history"]) > 1:
                import matplotlib.pyplot as plt
                st.subheader("Energy Convergence")
                fig, ax = plt.subplots(figsize=(9, 3))
                hist = res["toten_history"]
                ax.plot(range(1, len(hist)+1), hist, "b-o", ms=3)
                ax.set_xlabel("SCF step")
                ax.set_ylabel("TOTEN (eV)")
                ax.set_title("Electronic SCF convergence")
                ax.grid(alpha=0.4)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

    st.divider()
    st.subheader("OSZICAR (last 30 lines)")
    lines = tail_oszicar(work, 30)
    st.code("\n".join(lines) if lines else "— not found —", language="text")

    with st.expander("OUTCAR tail (50 lines)"):
        st.code("\n".join(tail_outcar(work, 50)) or "— not found —", language="text")

    st.divider()
    st.subheader("Download Output Files")
    dl_cols = st.columns(3)
    for i, fn in enumerate(["OUTCAR", "CONTCAR", "vasprun.xml", "DOSCAR", "PROCAR", "OSZICAR"]):
        fpath = work / fn
        if fpath.exists():
            dl_cols[i % 3].download_button(
                f"⬇️ {fn}", fpath.read_bytes(), fn, key=f"dl_{fn}"
            )

    st.divider()
    st.subheader("Launch Plot Scripts")
    plot_scripts = {
        "Band Structure":             "/home/shahi/bin/VASP/Plot/band_plot_vasp.py",
        "DOS":                        "/home/shahi/bin/VASP/Plot/dos_plot_vasp.py",
        "Band + DOS + Fatband":       "/home/shahi/bin/VASP/Plot/Band_DOS_FATBAND.py",
        "Interactive Procar Bandplot":"/home/shahi/bin/VASP/Plot/vasp_procar_bandplot_interactive.py",
    }
    for name, script in plot_scripts.items():
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"**{name}** — `{Path(script).name}`")
        if c2.button(f"Run", key=f"plot_{name}"):
            if Path(script).exists():
                try:
                    subprocess.Popen(["python3", script], cwd=str(work))
                    st.success(f"Launched {name}")
                except Exception as e:
                    st.error(str(e))
            else:
                st.error(f"Script not found: {script}")


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────
[step_structure, step_incar, step_kpoints, step_potcar, step_review_run, step_results][ss.step]()
