"""Manual board swap — step 1/2, rollback, reset."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from frutool.config import LogCallback
from frutool.domain.fru_ops import clone_restore_summary
from frutool.presentation.services import (
    list_step1_backups,
    plan_step1_bin_path,
    resolve_step2_backup_path,
    run_rollback,
    run_step1_job,
    run_step2_job,
    validate_rollback,
    validate_step1_export,
    validate_step2_clone,
)

if TYPE_CHECKING:
    from frutool.presentation.controller.auto_swap_controller import AutoSwapController
    from frutool.presentation.controller.base import ApplicationHost
    from frutool.presentation.controller.conn_controller import ConnController
    from frutool.presentation.controller.swap_progress import SwapProgress


class ManualSwapController:
    """Manual step 1/2, rollback, and full progress reset."""

    def __init__(
        self,
        host: ApplicationHost,
        conn: ConnController,
        progress: SwapProgress,
        auto: AutoSwapController,
    ) -> None:
        self._host = host
        self._conn = conn
        self._progress = progress
        self._auto = auto

    def _old_credentials(self) -> tuple[str, str]:
        return self._conn.credentials(False)

    def _new_credentials(self) -> tuple[str, str]:
        return self._conn.credentials(True)

    def doStep1(self) -> None:
        sn = self._progress.old_board_sn.strip()
        user, pwd = self._old_credentials()
        err = validate_step1_export(sn, user, pwd)
        if err:
            title, message, kind = err
            getattr(self._host, f"request_{kind}")(title, message)
            return
        bin_path = plan_step1_bin_path(sn)
        existing = list_step1_backups(sn)

        def proceed():
            self._progress.set_step1_done(False)
            self._progress.set_step2_done(False)
            self._progress.set_new_board_fru_backup_path(None)
            self._progress.emit_progress_step()
            self._progress.refresh_capabilities()
            self._host.set_busy(True)
            bmc_ip = self._conn.bmc_ip

            def job(log: LogCallback):
                return run_step1_job(sn, user, pwd, bmc_ip, bin_path, log)

            self._host.run_worker(job, self._on_step1_done, log_tab="fru")

        if existing:
            self._host.request_question(
                "备份已存在",
                f"已找到现有备份：{existing[-1]}\n是否创建新的带时间戳备份？",
                lambda ok: proceed() if ok else None,
            )
            return
        proceed()

    def _on_step1_done(self, result: object) -> None:
        self._host.set_busy(False)
        self._conn.apply_bmc_state_from_result(result)
        if isinstance(result, dict) and result.get("ok"):
            self._progress.set_step1_done(True)
            self._progress.set_last_synced_sn(self._progress.old_board_sn.strip())
            self._progress.emit_progress_step()
            self._progress.refresh_capabilities()
            self._host.request_info(
                "步骤 1 完成",
                "旧板 FRU 备份已导出。请连接新主板后执行步骤 2。",
            )
        else:
            self._progress.set_step1_done(False)
            self._progress.emit_progress_step()
            data = result if isinstance(result, dict) else {}
            self._host.request_critical(data.get("title", "失败"), data.get("message", "步骤 1 失败。"))

    def doStep2(self) -> None:
        sn = self._progress.old_board_sn.strip()
        user, pwd = self._new_credentials()
        err = validate_step2_clone(sn, user, pwd)
        if err:
            title, message, kind = err
            getattr(self._host, f"request_{kind}")(title, message)
            return
        old_bin_path, name = resolve_step2_backup_path(sn)
        if not old_bin_path:
            self._host.request_critical(
                "未找到备份",
                f"未找到 SN={sn} 的 FRU 备份，请先执行步骤 1。",
            )
            return
        self._host.log("info", f"Using old board backup: {name}")
        self._host.set_busy(True)
        bmc_ip = self._conn.bmc_ip

        def job(log: LogCallback):
            return run_step2_job(sn, user, pwd, bmc_ip, old_bin_path, log)

        self._host.run_worker(job, self._on_step2_done, log_tab="fru")

    def _on_step2_done(self, result: object) -> None:
        self._host.set_busy(False)
        self._conn.apply_bmc_state_from_result(result)
        if isinstance(result, dict) and result.get("ok"):
            self._progress.set_step2_done(True)
            self._progress.set_new_board_serial_backup(result.get("serial"))
            self._progress.set_new_board_fru_backup_path(result.get("rollback") or None)
            self._auto.clear_session()
            self._progress.emit_progress_step()
            self._progress.refresh_capabilities()
            self._host.request_info("步骤 2 完成", clone_restore_summary(result))
        else:
            self._progress.emit_progress_step()
            data = result if isinstance(result, dict) else {}
            self._host.request_critical(data.get("title", "失败"), data.get("message", "步骤 2 失败。"))

    def doRollback(self) -> None:
        path = self._progress.new_board_fru_backup_path
        err = validate_rollback(path)
        if err:
            title, message, kind = err
            getattr(self._host, f"request_{kind}")(title, message)
            return

        def proceed():
            user, pwd = self._new_credentials()
            bmc_ip = self._conn.bmc_ip
            self._host.set_busy(True)

            def job(log: LogCallback):
                return run_rollback(user, pwd, bmc_ip, path, log)

            self._host.run_worker(job, self._on_rollback_done, log_tab="fru")

        self._host.request_question(
            "确认回滚",
            f"是否恢复新板原始 FRU？\n{os.path.basename(path)}",
            lambda ok: proceed() if ok else None,
        )

    def _on_rollback_done(self, result: object) -> None:
        self._host.set_busy(False)
        if isinstance(result, dict) and result.get("ok"):
            self._host.log("success", "Rollback completed")
            self._host.request_info("回滚完成", "新板 FRU 已恢复。")
        else:
            self._host.log("error", "回滚失败")
            self._host.request_critical("回滚失败", "FRU 写入失败，请查看日志。")

    def doSwapReset(self) -> None:
        if self._host.busy:
            self._host.request_warning("忙碌", "当前有任务正在执行，请稍后再重置。")
            return
        has_progress = (
            self._progress.step1_done
            or self._progress.step2_done
            or bool(self._progress.old_board_sn.strip())
            or self._auto.has_running_auto_phase()
        )

        def proceed():
            self._auto.reset(switch_manual=True)
            self._auto.clear_session()
            self._progress.clear_all_progress()
            self._auto.clear_runtime_state()
            self._progress.emit_progress_step()
            self._auto.update_status()
            self._host.log("info", "换板进度已重置，已切回手动模式")
            self._progress.refresh_capabilities()

        if has_progress:
            self._host.request_question(
                "重置进度",
                "将清空本台换板进度、停止自动等待，并切回手动模式。\n"
                "已保存的 .bin 备份文件不会删除。\n\n是否继续？",
                lambda ok: proceed() if ok else None,
            )
            return
        proceed()
