"""Cloud detection utilities."""
from __future__ import annotations
import os

IS_CLOUD: bool = (
    os.getenv("STREAMLIT_SHARING_MODE") == "streamlit_sharing"
    or os.getenv("IS_CLOUD", "").lower() in ("1", "true", "yes")
)


def setup_auth() -> bool:
    return False


def is_pro() -> bool:
    return True


def is_logged_in() -> bool:
    return True


def pro_gate(feature: str) -> bool:
    return True


def upgrade_banner() -> None:
    pass
