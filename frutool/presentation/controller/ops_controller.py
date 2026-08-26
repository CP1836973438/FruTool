"""Ops controller — FRU batch write and PCIe topology write."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.config import (
    LogCallback,
    list_pcie_eeprom_tools,
    load_topo_script_pref,
    save_topo_script_pref,
)
from frutool.demo import hardware_sim_enabled, topo_demo_enabled
from frutool.presentation.controller.base import ApplicationHost
from frutool.presentation.dialogs.file_dialogs import browse_topo_file
from frutool.presentation.services import (
    run_fru_batch_write_resolved,
    run_fru_hint_read,
    run_topo_catalog_pick,
    run_topo_preload,
    run_topo_write,
    summarize_fru_batch_result,
    validate_fru_batch_write,
    validate_topo_write,
)

if TYPE_CHECKING:
    from frutool.presentation.controller.chrome_controller import ChromeController
    from frutool.presentation.controller.conn_controller import ConnController
    from frutool.presentation.controller.swap_controller import SwapController


class OpsController(QObject):
    """FRU field batch write and topology file write."""

    topoPathChanged = pyqtSignal()
    topoProgressVisibleChanged = pyqtSignal()
    topoMatchMessageChanged = pyqtSignal()
    topoMatchOkChanged = pyqtSignal()
    topoMatchBusyChanged = pyqtSignal()
    topoCandidatesChanged = pyqtSignal()
    topoCatalogChanged = pyqtSignal()
    selectedTopoCandidateIdChanged = pyqtSignal()
    selectedTopoCatalogIdChanged = pyqtSignal()
    catalogFilterChanged = pyqtSignal()
    topoScriptModelChanged = pyqtSignal()
    selectedTopoScriptIndexChanged = pyqtSignal()
    capabilitiesChanged = pyqtSignal()

    def __init__(
        self,
        host: ApplicationHost,
        conn: ConnController,
        swap: SwapController,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._host = host
        self._conn = conn
        self._swap = swap
        self._topo_path = ""
        self._topo_progress_visible = False
        self._topo_match_message = ""
        self._topo_match_ok = False
        self._topo_match_busy = False
        self._topo_candidates: list[dict] = []
        self._topo_catalog: list[dict] = []
        self._selected_topo_candidate_id = ""
        self._selected_topo_catalog_id = ""
        self._catalog_filter = ""
        self._topo_script_model: list[dict] = []
        self._selected_topo_script_index = -1
        self._fru_hint_in_flight = False
        self._topo_match_in_flight = False
        self._chrome: Optional[ChromeController] = None
        swap.capabilitiesChanged.connect(self.capabilitiesChanged.emit)

        self._fru_hint_timer = QTimer(self)
        self._fru_hint_timer.setSingleShot(True)
        self._fru_hint_timer.setInterval(400)
        self._fru_hint_timer.timeout.connect(self._run_fru_hint_read)

        self._conn.connFieldChanged.connect(self._on_conn_field_changed)

        self._refresh_topo_scripts(persist=False)

        if self._conn.bmcOnline:
            self._schedule_fru_hint_read()

    def bind_chrome(self, chrome: ChromeController) -> None:
        self._chrome = chrome
        chrome.currentPageChanged.connect(self._on_topo_page_entered)
        self._host.fru_field_model.hintsChanged.connect(self._on_fru_hints_updated)

    @property
    def fru_field_model(self):
        return self._host.fru_field_model

    # --- Capabilities ---

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canFruWrite(self) -> bool:
        return self._swap.canFruWrite

    @pyqtProperty(bool, notify=capabilitiesChanged)
    def canTopoWrite(self) -> bool:
        return self._swap.canTopoWrite

    @pyqtProperty(bool, constant=True)
    def demoMode(self) -> bool:
        return topo_demo_enabled()

    # --- State properties ---

    @pyqtProperty(str, notify=topoPathChanged)
    def topoPath(self) -> str:
        return self._topo_path

    @pyqtSlot(str)
    def setTopoPath(self, path: str) -> None:
        if path == self._topo_path:
            return
        self._topo_path = path
        self.topoPathChanged.emit()

    @pyqtProperty(bool, notify=topoProgressVisibleChanged)
    def topoProgressVisible(self) -> bool:
        return self._topo_progress_visible

    @pyqtProperty(str, notify=topoMatchMessageChanged)
    def topoMatchMessage(self) -> str:
        return self._topo_match_message

    @pyqtProperty(bool, notify=topoMatchOkChanged)
    def topoMatchOk(self) -> bool:
        return self._topo_match_ok

    @pyqtProperty(bool, notify=topoMatchBusyChanged)
    def topoMatchBusy(self) -> bool:
        return self._topo_match_busy

    @pyqtProperty("QVariantList", notify=topoCandidatesChanged)
    def topoCandidates(self) -> list:
        return self._topo_candidates

    @pyqtProperty("QVariantList", notify=topoCatalogChanged)
    def topoCatalog(self) -> list:
        if not self._catalog_filter.strip():
            return self._topo_catalog
        query = self._catalog_filter.strip().casefold()
        return [
            item
            for item in self._topo_catalog
            if query in str(item.get("manufacturer", "")).casefold()
            or query in str(item.get("platform", "")).casefold()
            or query in str(item.get("suite", "")).casefold()
            or query in str(item.get("archive", "")).casefold()
        ]

    @pyqtProperty(str, notify=selectedTopoCandidateIdChanged)
    def selectedTopoCandidateId(self) -> str:
        return self._selected_topo_candidate_id

    @pyqtProperty(str, notify=selectedTopoCatalogIdChanged)
    def selectedTopoCatalogId(self) -> str:
        return self._selected_topo_catalog_id

    @pyqtProperty(str, notify=catalogFilterChanged)
    def catalogFilter(self) -> str:
        return self._catalog_filter

    @pyqtSlot(str)
    def setCatalogFilter(self, text: str) -> None:
        if text == self._catalog_filter:
            return
        self._catalog_filter = text
        self.catalogFilterChanged.emit()
        self.topoCatalogChanged.emit()

    @pyqtProperty("QVariantList", notify=topoScriptModelChanged)
    def topoScriptModel(self) -> list:
        return self._topo_script_model

    @pyqtProperty(int, notify=selectedTopoScriptIndexChanged)
    def selectedTopoScriptIndex(self) -> int:
        return self._selected_topo_script_index

    def _selected_topo_script_path(self) -> str:
        if 0 <= self._selected_topo_script_index < len(self._topo_script_model):
            return str(self._topo_script_model[self._selected_topo_script_index].get("path", ""))
        return ""

    def _refresh_topo_scripts(self, *, persist: bool) -> None:
        tools = list_pcie_eeprom_tools()
        pref = load_topo_script_pref()
        self._topo_script_model = [
            {"label": t["label"], "path": t["path"], "id": t["id"]} for t in tools
        ]
        index = -1
        if pref:
            for i, item in enumerate(self._topo_script_model):
                if os.path.normpath(str(item["path"])) == pref:
                    index = i
                    break
        if index < 0 and self._topo_script_model:
            index = 0
        self._selected_topo_script_index = index
        self.topoScriptModelChanged.emit()
        self.selectedTopoScriptIndexChanged.emit()
        if persist and index >= 0:
            save_topo_script_pref(self._selected_topo_script_path())

    @pyqtSlot(int)
    def setSelectedTopoScriptIndex(self, index: int) -> None:
        if index == self._selected_topo_script_index:
            return
        if index < 0 or index >= len(self._topo_script_model):
            return
        self._selected_topo_script_index = index
        self.selectedTopoScriptIndexChanged.emit()
        save_topo_script_pref(self._selected_topo_script_path())

    @pyqtSlot()
    def refreshTopoScripts(self) -> None:
        previous = self._selected_topo_script_path()
        self._refresh_topo_scripts(persist=False)
        if previous:
            for i, item in enumerate(self._topo_script_model):
                if os.path.normpath(str(item["path"])) == os.path.normpath(previous):
                    if i != self._selected_topo_script_index:
                        self._selected_topo_script_index = i
                        self.selectedTopoScriptIndexChanged.emit()
                    save_topo_script_pref(previous)
                    return
        if self._selected_topo_script_index >= 0:
            save_topo_script_pref(self._selected_topo_script_path())

    def _set_topo_match(self, *, busy: bool, ok: bool, message: str) -> None:
        if self._topo_match_busy != busy:
            self._topo_match_busy = busy
            self.topoMatchBusyChanged.emit()
        if self._topo_match_ok != ok:
            self._topo_match_ok = ok
            self.topoMatchOkChanged.emit()
        if self._topo_match_message != message:
            self._topo_match_message = message
            self.topoMatchMessageChanged.emit()

    def _set_topo_candidates(self, candidates: list[dict], selected_id: str = "") -> None:
        self._topo_candidates = candidates
        self.topoCandidatesChanged.emit()
        if selected_id != self._selected_topo_candidate_id:
            self._selected_topo_candidate_id = selected_id
            self.selectedTopoCandidateIdChanged.emit()
        if selected_id:
            if self._selected_topo_catalog_id:
                self._selected_topo_catalog_id = ""
                self.selectedTopoCatalogIdChanged.emit()

    def _set_selected_catalog_id(self, entry_id: str) -> None:
        if entry_id == self._selected_topo_catalog_id:
            return
        self._selected_topo_catalog_id = entry_id
        self.selectedTopoCatalogIdChanged.emit()
        if entry_id:
            if self._selected_topo_candidate_id:
                self._selected_topo_candidate_id = ""
                self.selectedTopoCandidateIdChanged.emit()
                for item in self._topo_candidates:
                    item["selected"] = False
                self.topoCandidatesChanged.emit()

    def _set_topo_catalog(self, catalog: list[dict]) -> None:
        self._topo_catalog = catalog
        self.topoCatalogChanged.emit()

    def _apply_preload_result(self, result: dict) -> None:
        candidates = list(result.get("candidates") or [])
        self._set_topo_catalog(list(result.get("catalog") or []))
        selected_id = ""
        path = ""
        if candidates:
            picked = next((c for c in candidates if c.get("selected")), candidates[0])
            selected_id = str(picked.get("id", ""))
            path = str(picked.get("path", ""))
            for item in candidates:
                item["selected"] = item.get("id") == selected_id
        self._set_topo_candidates(candidates, selected_id)
        if path and os.path.isfile(path):
            self.setTopoPath(path)
        else:
            self.setTopoPath("")

    @pyqtSlot(str)
    def selectTopoCandidate(self, entry_id: str) -> None:
        entry_id = (entry_id or "").strip()
        if not entry_id or not self._topo_candidates:
            return
        path = ""
        updated: list[dict] = []
        for item in self._topo_candidates:
            row = dict(item)
            row["selected"] = row.get("id") == entry_id
            if row["selected"]:
                path = str(row.get("path", ""))
            updated.append(row)
        if not path or not os.path.isfile(path):
            return
        self._set_topo_candidates(updated, entry_id)
        self.setTopoPath(path)
        mfr = next((str(c.get("manufacturer", "")) for c in updated if c.get("selected")), "")
        platform = next((str(c.get("platform", "")) for c in updated if c.get("selected")), "")
        suite = next((str(c.get("suite", "")) for c in updated if c.get("selected")), "")
        label = f"{mfr} · {platform}" if platform else mfr
        self._set_topo_match(
            busy=False,
            ok=True,
            message=f"已选择 {label} / {suite}，请确认后刷写。",
        )

    @pyqtSlot(str)
    def selectTopoCatalogEntry(self, entry_id: str) -> None:
        entry_id = (entry_id or "").strip()
        if not entry_id or self._topo_match_in_flight:
            return
        self._topo_match_in_flight = True
        self._set_topo_match(busy=True, ok=False, message="正在加载所选拓扑文件…")

        def job(log: LogCallback):
            return run_topo_catalog_pick(entry_id, log)

        def done(result: object) -> None:
            self._topo_match_in_flight = False
            if isinstance(result, dict) and result.get("ok") and result.get("path"):
                self._set_topo_candidates([], "")
                self.setTopoPath(str(result["path"]))
                self._set_selected_catalog_id(str(result.get("id", entry_id)))
                self._set_topo_match(
                    busy=False,
                    ok=True,
                    message=str(result.get("message", "已从拓扑库加载。")),
                )
            else:
                message = "加载拓扑失败。"
                if isinstance(result, dict) and result.get("message"):
                    message = str(result["message"])
                self._set_topo_match(busy=False, ok=False, message=message)

        self._host.run_worker(job, done, log_tab="topo")

    # --- FRU hints ---

    @pyqtSlot()
    def on_bmc_online_changed(self) -> None:
        if topo_demo_enabled():
            return
        if not self._conn.bmcOnline:
            self._fru_hint_timer.stop()
            self._host.fru_field_model.clearAllHints()
            self._set_topo_candidates([], "")
            self._set_topo_catalog([])
            self._set_selected_catalog_id("")
            return
        self._schedule_fru_hint_read()

    def _on_conn_field_changed(self, _field: str) -> None:
        if self._conn.bmcOnline:
            self._schedule_fru_hint_read()

    def _schedule_fru_hint_read(self) -> None:
        if topo_demo_enabled():
            return
        if not self._conn.bmcOnline:
            return
        self._fru_hint_timer.start()

    def _run_fru_hint_read(self) -> None:
        if not self._conn.bmcOnline or self._fru_hint_in_flight:
            return
        new_user, new_pwd = self._conn.credentials(True)
        old_user, old_pwd = self._conn.credentials(False)
        bmc_ip = self._conn.bmc_ip
        self._fru_hint_in_flight = True

        def job(log: LogCallback):
            return run_fru_hint_read(bmc_ip, new_user, new_pwd, old_user, old_pwd, log)

        def done(result: object) -> None:
            self._fru_hint_in_flight = False
            if isinstance(result, dict) and result:
                self._host.fru_field_model.setHints(result)
            else:
                self._host.fru_field_model.clearAllHints()

        self._host.run_worker(job, done, log_tab="fru")

    def _on_topo_page_entered(self) -> None:
        if self._chrome and self._chrome.currentPage == "topo":
            self._try_topo_match()

    def _on_fru_hints_updated(self) -> None:
        if self._chrome and self._chrome.currentPage == "topo":
            self._try_topo_match()

    def _try_topo_match(self) -> None:
        if not self._conn.bmcOnline:
            self._set_topo_match(
                busy=False,
                ok=False,
                message="BMC 未连接，无法读取新板 FRU。",
            )
            return
        if self._fru_hint_in_flight:
            self._set_topo_match(
                busy=True,
                ok=False,
                message="正在读取新板 FRU 信息…",
            )
            return
        hint = self._host.fru_field_model.hint_for_name("Product Extra")
        manufacturer = self._host.fru_field_model.hint_for_name("Product Manufacturer")
        if not hint.strip():
            self._set_topo_match(
                busy=False,
                ok=False,
                message="未能读取到 Product Extra（套餐号），请确认新板 FRU 可访问。",
            )
            return
        if self._topo_match_in_flight:
            return
        self._topo_match_in_flight = True
        self._set_topo_match(
            busy=True,
            ok=False,
            message="正在根据套餐号匹配套餐拓扑文件…",
        )

        def job(log: LogCallback):
            return run_topo_preload(hint, manufacturer, log)

        def done(result: object) -> None:
            self._topo_match_in_flight = False
            if isinstance(result, dict):
                self._set_topo_match(
                    busy=False,
                    ok=bool(result.get("ok")),
                    message=str(result.get("message", "")),
                )
                self._apply_preload_result(result)
            else:
                self._set_topo_candidates([], "")
                self._set_topo_catalog([])
                self._set_topo_match(
                    busy=False,
                    ok=False,
                    message="拓扑匹配套餐失败。",
                )

        self._host.run_worker(job, done, log_tab="topo")

    # --- FRU batch ---

    @pyqtSlot()
    def doFruBatchWrite(self) -> None:
        new_user, new_pwd = self._conn.credentials(True)
        old_user, old_pwd = self._conn.credentials(False)
        fields = self._host.fru_field_model.nonEmptyFields()
        err = validate_fru_batch_write(new_user, new_pwd, old_user, old_pwd, fields)
        if err:
            title, message, kind = err
            getattr(self._host, f"request_{kind}")(title, message)
            return

        def proceed():
            bmc_ip = self._conn.bmc_ip
            self._host.set_busy(True)

            def job(log: LogCallback):
                if hardware_sim_enabled():
                    for area, idx, value in fields:
                        log("info", f"[演示] 模拟写入 FRU field {area}/{idx} = {value}")
                    log("success", "[演示] FRU 字段刷写完成（未连接真实硬件）")
                    return {"ok": True, "success": len(fields), "total": len(fields), "cred_failed": False}
                return run_fru_batch_write_resolved(
                    bmc_ip, new_user, new_pwd, old_user, old_pwd, fields, log
                )

            self._host.run_worker(job, self._on_fru_batch_done, log_tab="fru")

        self._host.request_question(
            "确认",
            f"将刷写 {len(fields)} 个 FRU 字段，是否继续？",
            lambda ok: proceed() if ok else None,
        )

    def _on_fru_batch_done(self, result: object) -> None:
        self._host.set_busy(False)
        level, log_line, dialog = summarize_fru_batch_result(result)
        self._host.log(level, log_line)
        if isinstance(result, dict) and result.get("cred_failed"):
            self._host.request_warning("失败", dialog)
        else:
            self._host.request_info("完成", dialog)

    # --- Topology ---

    @pyqtSlot()
    def doTopoWrite(self) -> None:
        path = self._topo_path.strip()
        script_path = self._selected_topo_script_path()
        user, pwd = self._conn.credentials(True)
        err = validate_topo_write(path, user, pwd, script_path=script_path)
        if err:
            title, message, kind = err
            getattr(self._host, f"request_{kind}")(title, message)
            return
        bmc_ip = self._conn.bmc_ip
        self._host.set_busy(True)
        self._topo_progress_visible = True
        self.topoProgressVisibleChanged.emit()

        def job(log: LogCallback):
            if hardware_sim_enabled():
                log("cmd", f"[演示] PcieEEpromTool.py -W {path}")
                log("info", f"[演示] 脚本={script_path or '(默认)'} · BMC={bmc_ip}")
                log("success", "[演示] Topology file write completed（未连接真实硬件）")
                return {"ok": True}
            return run_topo_write(path, user, pwd, bmc_ip, log, script_path=script_path)

        self._host.run_worker(job, self._on_topo_done, log_tab="topo")

    def _on_topo_done(self, result: object) -> None:
        self._topo_progress_visible = False
        self.topoProgressVisibleChanged.emit()
        self._host.set_busy(False)
        if isinstance(result, dict) and result.get("ok"):
            self._host.request_info("完成", "拓扑文件写入已完成。")
        else:
            self._host.request_critical("失败", "拓扑写入失败，请查看日志。")

    @pyqtSlot()
    def browseTopoFile(self) -> None:
        path = browse_topo_file(self._topo_path)
        if path:
            self.setTopoPath(path)
