"""Cloud detection and subscription plan utilities."""
from __future__ import annotations
import os
import streamlit as st

IS_CLOUD: bool = (
    os.getenv("STREAMLIT_SHARING_MODE") == "streamlit_sharing"
    or os.getenv("IS_CLOUD", "").lower() in ("1", "true", "yes")
)

FREE_CALC_TYPES: frozenset[str] = frozenset({"scf"})

STRIPE_MONTHLY_LINK = "https://buy.stripe.com/REPLACE_ME_MONTHLY"
STRIPE_YEARLY_LINK  = "https://buy.stripe.com/REPLACE_ME_YEARLY"

UPGRADE_URL = STRIPE_MONTHLY_LINK


def _auth_configured() -> bool:
    try:
        return "STRIPE_API_KEY" in st.secrets
    except Exception:
        return False


def setup_auth() -> bool:
    """
    Call once at app startup. Returns True if paywall is active.
    Local dev (no secrets): skips auth entirely.
    """
    if not _auth_configured():
        return False
    try:
        from streamlit_paywall import add_auth  # type: ignore
        add_auth(required=False)
        return True
    except Exception:
        return False


def is_pro() -> bool:
    """True if the user has an active Pro subscription — or if running locally."""
    if not IS_CLOUD:
        return True
    return st.session_state.get("user_subscribed", False)


def is_logged_in() -> bool:
    return bool(st.session_state.get("email", ""))


def pro_gate(feature: str) -> bool:
    """
    Returns True if user can proceed. Shows upgrade prompt and returns False otherwise.
    Use as: if not pro_gate("Band structure"): return
    """
    if is_pro():
        return True
    st.warning(
        f"⭐ **{feature}** is a Pro feature. "
        f"[Upgrade to Pro →]({UPGRADE_URL})"
    )
    return False


def upgrade_banner() -> None:
    """Compact inline upgrade call-to-action."""
    if IS_CLOUD and not is_pro():
        st.info(
            f"🔓 Unlock all features with **Pro** — $9/month or $79/year.  "
            f"[Monthly]({STRIPE_MONTHLY_LINK}) · [Yearly]({STRIPE_YEARLY_LINK})"
        )
