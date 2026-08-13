"""Theme tokens and helpers (no Qt widget dependencies)."""
from __future__ import annotations

import sys
from typing import Optional

SPACING = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
FONT = {"title": 14, "subtitle": 13, "body": 12, "caption": 11, "small": 10}

THEMES = {
    "dark": {
        "bg": "#1C1E22",
        "surface": "#27292E",
        "surface2": "#2D3035",
        "surface3": "#383B41",
        "border": "#3D3F43",
        "accent": "#3B82F6",
        "accent_hover": "#5595F8",
        "accent_dim": "#3B6EC0",
        "success": "#30d158",
        "warning": "#ff9f0a",
        "error": "#ff453a",
        "text": "#E2E2E2",
        "text2": "#B5B5B5",
        "text3": "#898989",
        "terminal_bg": "#1C1E22",
        "log_info": "#A9B7C6",
        "input_bg": "#383B41",
        "chrome_bg": "#383B41",
        "chrome_sidebar": "#27292E",
        "chrome_status": "#27292E",
        "chrome_border": "#303235",
        "window_btn_hover": "#3E3E42",
        "window_btn_close_hover": "#E81123",
        "window_btn_icon": "#CCCCCC",
        "window_btn_icon_disabled": "#64646A",
        "btn_secondary_bg": "#2D3035",
        "btn_secondary_border": "#3D3F43",
        "btn_secondary_hover": "#383B41",
        "btn_primary_bg": "#3B82F6",
        "btn_primary_fg": "#FFFFFF",
        "btn_danger_fg": "#ff453a",
        "btn_danger_border": "#ff453a",
        "focus_border": "#3B82F6",
        "focus_glow": "#603B6EC0",
        "icon_muted": "#9A9A9A",
        "icon_accent": "#3B82F6",
        "badge_success": "#30d158",
        "badge_warning": "#ff9f0a",
        "badge_error": "#ff453a",
        "scrollbar_handle": "#48484D",
        "scrollbar_handle_hover": "#6C6C72",
        "chrome_bg_top": "#3E4145",
        "chrome_bg_bottom": "#36393D",
        "chrome_sidebar_top": "#2D2F33",
        "chrome_sidebar_bottom": "#26272B",
        "chrome_sidebar_edge": "#232429",
        "chrome_status_top": "#2D2F33",
        "chrome_status_bottom": "#26272B",
        "surface_top": "#2C2E32",
        "surface_bottom": "#26272B",
        "glass_card": "rgba(255,255,255,0.09)",
        "glass_card_opacity": 0.36,
        "glass_dialog": "rgba(255,255,255,0.12)",
        "glass_dialog_opacity": 0.50,
        "dialog_backing_opacity": 0.76,
        "glass_blur": 28,
        "glow_strength": 0.9,
        "accent_flow_speed": 0.22,
    },
    "light": {
        "bg": "#F2F2F2",
        "surface": "#FFFFFF",
        "surface2": "#F0F0F0",
        "surface3": "#E8E8E8",
        "accent": "#3B82F6",
        "accent_hover": "#3182E5",
        "accent_dim": "#BFD5FB",
        "success": "#1f9d4c",
        "warning": "#c77700",
        "error": "#d70015",
        "text": "#202020",
        "text2": "#4F4F4F",
        "text3": "#686868",
        "terminal_bg": "#F0F0F0",
        "log_info": "#2B2B2B",
        "input_bg": "#FFFFFF",
        "chrome_bg": "#F5F5F5",
        "chrome_sidebar": "#E8E8E8",
        "chrome_status": "#E8E8E8",
        "chrome_border": "#C8C8C8",
        "border": "#D0D0D0",
        "window_btn_hover": "#D0D0D0",
        "window_btn_close_hover": "#E81123",
        "window_btn_icon": "#5C5C5C",
        "window_btn_icon_disabled": "#AAAAAA",
        "btn_secondary_bg": "#F0F0F0",
        "btn_secondary_border": "#D4D4D4",
        "btn_secondary_hover": "#E8E8E8",
        "btn_primary_bg": "#3B82F6",
        "btn_primary_fg": "#FFFFFF",
        "btn_danger_fg": "#d70015",
        "btn_danger_border": "#d70015",
        "focus_border": "#3B82F6",
        "focus_glow": "#403B82F6",
        "icon_muted": "#5C5C5C",
        "icon_accent": "#3B82F6",
        "badge_success": "#1f9d4c",
        "badge_warning": "#c77700",
        "badge_error": "#d70015",
        "scrollbar_handle": "#C8C8C8",
        "scrollbar_handle_hover": "#8C8C8C",
        "chrome_bg_top": "#FAFAFA",
        "chrome_bg_bottom": "#F0F0F0",
        "chrome_sidebar_top": "#EDEDED",
        "chrome_sidebar_bottom": "#E3E3E3",
        "chrome_sidebar_edge": "#DEDEDE",
        "chrome_status_top": "#EDEDED",
        "chrome_status_bottom": "#E3E3E3",
        "surface_top": "#FFFFFF",
        "surface_bottom": "#F8F8F8",
        "glass_card": "#FFFFFF",
        "glass_card_opacity": 0.42,
        "glass_dialog": "rgba(0,0,0,0.08)",
        "glass_dialog_opacity": 0.38,
        "dialog_backing_opacity": 0.82,
        "glass_blur": 24,
        "glow_strength": 0.78,
        "accent_flow_speed": 0.18,
    },
}

LOG_LEVEL_PREFIX = {
    "success": "SUCCESS",
    "error": "ERR",
    "warning": "WARN",
    "cmd": "$",
    "info": "INFO",
}


def read_windows_light_mode() -> Optional[bool]:
    if sys.platform != "win32":
        return None
    try:
        import winreg

        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return bool(value)
    except Exception:
        return None


def resolve_theme_key(theme_mode: str, last_system_light: Optional[bool]) -> tuple[str, Optional[bool]]:
    if theme_mode in ("dark", "light"):
        return theme_mode, last_system_light
    light = read_windows_light_mode()
    return ("light" if light else "dark"), light


def theme_color(theme_key: str, token: str) -> str:
    return THEMES.get(theme_key, THEMES["dark"]).get(token, "#FFFFFF")


def log_color(theme_key: str, level: str) -> str:
    c = THEMES[theme_key]
    if level == "info":
        return c.get("log_info", c["text"])
    return {
        "success": c["success"],
        "error": c["error"],
        "warning": c["warning"],
        "cmd": c["accent"],
    }.get(level, c["text"])


def log_prefix(level: str) -> str:
    return LOG_LEVEL_PREFIX.get(level, "INFO")
