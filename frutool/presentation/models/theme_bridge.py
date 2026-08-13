"""Resolved theme tokens exposed to QML."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

from frutool.gpu_policy import shader_effects_enabled
from frutool.theme.tokens import FONT, SPACING, THEMES


class ThemeBridge(QObject):
    """Exposes resolved theme tokens to QML."""

    themeKeyChanged = pyqtSignal()
    layoutEffectsPausedChanged = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._theme_key = "dark"
        self._shader_effects_enabled = shader_effects_enabled()
        # 静态抓屏 + 关闭 chrome 递归模糊后，独显可安全启用液态玻璃
        self._use_liquid_glass = self._shader_effects_enabled
        self._layout_effects_paused = False

    def _c(self, token: str) -> str:
        return THEMES.get(self._theme_key, THEMES["dark"]).get(token, "#FFFFFF")

    @pyqtProperty(str, notify=themeKeyChanged)
    def themeKey(self) -> str:
        return self._theme_key

    def setThemeKey(self, theme_key: str) -> None:
        if theme_key == self._theme_key:
            return
        self._theme_key = theme_key
        self.themeKeyChanged.emit()

    @pyqtProperty(str, notify=themeKeyChanged)
    def bg(self) -> str:
        return self._c("bg")

    @pyqtProperty(str, notify=themeKeyChanged)
    def surface(self) -> str:
        return self._c("surface")

    @pyqtProperty(str, notify=themeKeyChanged)
    def surface2(self) -> str:
        return self._c("surface2")

    @pyqtProperty(str, notify=themeKeyChanged)
    def surface3(self) -> str:
        return self._c("surface3")

    @pyqtProperty(str, notify=themeKeyChanged)
    def surface_top(self) -> str:
        return self._c("surface_top")

    @pyqtProperty(str, notify=themeKeyChanged)
    def surface_bottom(self) -> str:
        return self._c("surface_bottom")

    @pyqtProperty(str, notify=themeKeyChanged)
    def border(self) -> str:
        return self._c("border")

    @pyqtProperty(str, notify=themeKeyChanged)
    def accent(self) -> str:
        return self._c("accent")

    @pyqtProperty(str, notify=themeKeyChanged)
    def accent_hover(self) -> str:
        return self._c("accent_hover")

    @pyqtProperty(str, notify=themeKeyChanged)
    def accent_dim(self) -> str:
        return self._c("accent_dim")

    @pyqtProperty(str, notify=themeKeyChanged)
    def success(self) -> str:
        return self._c("success")

    @pyqtProperty(str, notify=themeKeyChanged)
    def warning(self) -> str:
        return self._c("warning")

    @pyqtProperty(str, notify=themeKeyChanged)
    def error(self) -> str:
        return self._c("error")

    @pyqtProperty(str, notify=themeKeyChanged)
    def text(self) -> str:
        return self._c("text")

    @pyqtProperty(str, notify=themeKeyChanged)
    def text2(self) -> str:
        return self._c("text2")

    @pyqtProperty(str, notify=themeKeyChanged)
    def text3(self) -> str:
        return self._c("text3")

    @pyqtProperty(str, notify=themeKeyChanged)
    def terminal_bg(self) -> str:
        return self._c("terminal_bg")

    @pyqtProperty(str, notify=themeKeyChanged)
    def glass_card(self) -> str:
        return self._c("glass_card")

    @pyqtProperty(float, notify=themeKeyChanged)
    def glass_card_opacity(self) -> float:
        return float(THEMES.get(self._theme_key, THEMES["dark"]).get("glass_card_opacity", 0.22))

    @pyqtProperty(str, notify=themeKeyChanged)
    def glass_dialog(self) -> str:
        return self._c("glass_dialog")

    @pyqtProperty(float, notify=themeKeyChanged)
    def glass_dialog_opacity(self) -> float:
        return float(THEMES.get(self._theme_key, THEMES["dark"]).get("glass_dialog_opacity", 0.35))

    @pyqtProperty(float, notify=themeKeyChanged)
    def dialog_backing_opacity(self) -> float:
        return float(THEMES.get(self._theme_key, THEMES["dark"]).get("dialog_backing_opacity", 0.76))

    @pyqtProperty(str, notify=themeKeyChanged)
    def log_info(self) -> str:
        return self._c("log_info")

    @pyqtProperty(str, notify=themeKeyChanged)
    def input_bg(self) -> str:
        return self._c("input_bg")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_bg(self) -> str:
        return self._c("chrome_bg")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_bg_top(self) -> str:
        return self._c("chrome_bg_top")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_bg_bottom(self) -> str:
        return self._c("chrome_bg_bottom")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_sidebar(self) -> str:
        return self._c("chrome_sidebar")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_sidebar_top(self) -> str:
        return self._c("chrome_sidebar_top")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_sidebar_bottom(self) -> str:
        return self._c("chrome_sidebar_bottom")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_status(self) -> str:
        return self._c("chrome_status")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_status_top(self) -> str:
        return self._c("chrome_status_top")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_status_bottom(self) -> str:
        return self._c("chrome_status_bottom")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_border(self) -> str:
        return self._c("chrome_border")

    @pyqtProperty(str, notify=themeKeyChanged)
    def btn_primary_bg(self) -> str:
        return self._c("btn_primary_bg")

    @pyqtProperty(str, notify=themeKeyChanged)
    def btn_primary_fg(self) -> str:
        return self._c("btn_primary_fg")

    @pyqtProperty(str, notify=themeKeyChanged)
    def btn_secondary_bg(self) -> str:
        return self._c("btn_secondary_bg")

    @pyqtProperty(str, notify=themeKeyChanged)
    def btn_secondary_border(self) -> str:
        return self._c("btn_secondary_border")

    @pyqtProperty(str, notify=themeKeyChanged)
    def btn_secondary_hover(self) -> str:
        return self._c("btn_secondary_hover")

    @pyqtProperty(str, notify=themeKeyChanged)
    def window_btn_hover(self) -> str:
        return self._c("window_btn_hover")

    @pyqtProperty(str, notify=themeKeyChanged)
    def window_btn_close_hover(self) -> str:
        return self._c("window_btn_close_hover")

    @pyqtProperty(str, notify=themeKeyChanged)
    def window_btn_icon(self) -> str:
        return self._c("window_btn_icon")

    @pyqtProperty(str, notify=themeKeyChanged)
    def badge_success(self) -> str:
        return self._c("badge_success")

    @pyqtProperty(str, notify=themeKeyChanged)
    def badge_warning(self) -> str:
        return self._c("badge_warning")

    @pyqtProperty(str, notify=themeKeyChanged)
    def badge_error(self) -> str:
        return self._c("badge_error")

    @pyqtProperty(str, notify=themeKeyChanged)
    def scrollbar_handle(self) -> str:
        return self._c("scrollbar_handle")

    @pyqtProperty(int, notify=themeKeyChanged)
    def glass_blur(self) -> int:
        return int(THEMES.get(self._theme_key, THEMES["dark"]).get("glass_blur", 28))

    @pyqtProperty(float, notify=themeKeyChanged)
    def glow_strength(self) -> float:
        return float(THEMES.get(self._theme_key, THEMES["dark"]).get("glow_strength", 0.65))

    @pyqtProperty(float, notify=themeKeyChanged)
    def accent_flow_speed(self) -> float:
        return float(THEMES.get(self._theme_key, THEMES["dark"]).get("accent_flow_speed", 0.15))

    @pyqtProperty(str, notify=themeKeyChanged)
    def focus_border(self) -> str:
        return self._c("focus_border")

    @pyqtProperty(str, notify=themeKeyChanged)
    def focus_glow(self) -> str:
        return self._c("focus_glow")

    @pyqtProperty(str, notify=themeKeyChanged)
    def chrome_sidebar_edge(self) -> str:
        return self._c("chrome_sidebar_edge")

    @pyqtProperty(str, notify=themeKeyChanged)
    def icon_muted(self) -> str:
        return self._c("icon_muted")

    @pyqtProperty(str, notify=themeKeyChanged)
    def icon_accent(self) -> str:
        return self._c("icon_accent")

    @pyqtProperty(str, notify=themeKeyChanged)
    def btn_danger_fg(self) -> str:
        return self._c("btn_danger_fg")

    @pyqtProperty(str, notify=themeKeyChanged)
    def btn_danger_border(self) -> str:
        return self._c("btn_danger_border")

    @pyqtProperty(str, notify=themeKeyChanged)
    def scrollbar_handle_hover(self) -> str:
        return self._c("scrollbar_handle_hover")

    @pyqtProperty(str, notify=themeKeyChanged)
    def window_btn_icon_disabled(self) -> str:
        return self._c("window_btn_icon_disabled")

    # Font-size tokens
    @pyqtProperty(int, notify=themeKeyChanged)
    def fontSizeTitle(self) -> int:
        return FONT["title"]

    @pyqtProperty(int, notify=themeKeyChanged)
    def fontSizeSubtitle(self) -> int:
        return FONT["subtitle"]

    @pyqtProperty(int, notify=themeKeyChanged)
    def fontSizeBody(self) -> int:
        return FONT["body"]

    @pyqtProperty(int, notify=themeKeyChanged)
    def fontSizeCaption(self) -> int:
        return FONT["caption"]

    @pyqtProperty(int, notify=themeKeyChanged)
    def fontSizeSmall(self) -> int:
        return FONT["small"]

    @pyqtProperty(bool, constant=True)
    def shaderEffectsEnabled(self) -> bool:
        return self._shader_effects_enabled

    @pyqtProperty(bool, constant=True)
    def useLiquidGlass(self) -> bool:
        return self._use_liquid_glass and self._shader_effects_enabled

    @pyqtProperty(bool, constant=True)
    def liveBlurEnabled(self) -> bool:
        return False

    @pyqtProperty(bool, notify=layoutEffectsPausedChanged)
    def layoutEffectsPaused(self) -> bool:
        return self._layout_effects_paused

    @layoutEffectsPaused.setter
    def layoutEffectsPaused(self, paused: bool) -> None:
        if self._layout_effects_paused == paused:
            return
        self._layout_effects_paused = paused
        self.layoutEffectsPausedChanged.emit()

    # Z-index constants
    @pyqtProperty(int, constant=True)
    def zBackground(self) -> int:
        return 0

    @pyqtProperty(int, constant=True)
    def zContent(self) -> int:
        return 1

    @pyqtProperty(int, constant=True)
    def zOverlay(self) -> int:
        return 5

    @pyqtProperty(int, constant=True)
    def zRail(self) -> int:
        return 10

    @pyqtProperty(int, constant=True)
    def zPopup(self) -> int:
        return 100

    @pyqtProperty(int, constant=True)
    def zDragIndicator(self) -> int:
        return 100

    @pyqtProperty(int, notify=themeKeyChanged)
    def spacing_xs(self) -> int:
        return SPACING["xs"]

    @pyqtProperty(int, notify=themeKeyChanged)
    def spacing_sm(self) -> int:
        return SPACING["sm"]

    @pyqtProperty(int, notify=themeKeyChanged)
    def spacing_md(self) -> int:
        return SPACING["md"]

    @pyqtProperty(int, notify=themeKeyChanged)
    def spacing_lg(self) -> int:
        return SPACING["lg"]

    @pyqtProperty(int, notify=themeKeyChanged)
    def spacing_xl(self) -> int:
        return SPACING["xl"]
