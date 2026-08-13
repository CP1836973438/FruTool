"""PCIe topology catalog — index PCLE archives and bare .bin files; match by suite + manufacturer."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from typing import Callable, Optional

from frutool.config import (
    LOG_DIR,
    PCLE_DIR_NAME,
    PCLE_MANUFACTURERS,
    PCLE_PLATFORM_HINTS,
    TOPO_CACHE_DIR,
    TOPO_INDEX_JSON,
    resolve_pcle_dirs,
)

ARCHIVE_EXTS = {".zip", ".7z", ".rar"}
BARE_BIN_EXT = ".bin"
_MACOSX_MARK = "__macosx"
_SUITE_PREFIX = "suite:"
_INDEX_VERSION = 5
_UNKNOWN_MANUFACTURER = "未知厂商"

LogFn = Callable[[str, str], None]


@dataclass(frozen=True)
class TopoEntry:
    suite_code: str
    manufacturer: str
    platform: str
    archive_path: str
    inner_path: str
    archive_mtime: float
    entry_id: str


def parse_suite_code(product_extra: str) -> Optional[str]:
    """Extract suite code from FRU Product Extra (e.g. ``Suite:S62D1-I8DD2M-L``)."""
    text = (product_extra or "").strip()
    if not text:
        return None
    if text.lower().startswith(_SUITE_PREFIX):
        code = text.split(":", 1)[1].strip()
        return code or None
    return text


def _normalize_archive_tokens(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", name).upper()


def _norm_manufacturer(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").casefold())


def canonical_manufacturer(name: str) -> str:
    """Map manufacturer text to the canonical ``PCLE_MANUFACTURERS`` spelling (case-insensitive)."""
    raw = (name or "").strip()
    if not raw:
        return ""
    norm = _norm_manufacturer(raw)
    for manufacturer in PCLE_MANUFACTURERS:
        if _norm_manufacturer(manufacturer) == norm:
            return manufacturer
    for manufacturer in PCLE_MANUFACTURERS:
        token = _norm_manufacturer(manufacturer)
        if token and (token in norm or norm in token):
            return manufacturer
    return raw


def infer_manufacturer_from_archive(archive_path: str) -> str:
    """Parse manufacturer from PCLE archive / bare-bin path (filename + parent folders)."""
    return _infer_token_from_path(archive_path, PCLE_MANUFACTURERS) or _UNKNOWN_MANUFACTURER


def infer_platform_from_archive(archive_path: str) -> str:
    """Parse platform / 机型 code from archive / bare-bin path (case-insensitive)."""
    return _infer_token_from_path(archive_path, PCLE_PLATFORM_HINTS)


def _path_inference_blob(path: str) -> str:
    """Parent folders (until PCLE) + file stem — used to infer manufacturer/platform."""
    parts: list[str] = []
    directory = os.path.dirname(path)
    for _ in range(4):
        base = os.path.basename(directory.rstrip("\\/"))
        if not base or base.casefold() == PCLE_DIR_NAME.casefold():
            break
        parts.append(base)
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    parts.reverse()
    stem = os.path.splitext(os.path.basename(path))[0]
    if stem:
        parts.append(stem)
    return " ".join(parts)


def _infer_token_from_path(path: str, candidates: tuple[str, ...]) -> str:
    blob = _normalize_archive_tokens(_path_inference_blob(path))
    best = ""
    best_len = 0
    for candidate in candidates:
        token = _normalize_archive_tokens(candidate)
        if token and token in blob and len(token) > best_len:
            best = candidate
            best_len = len(token)
    return best


def infer_vendor_label(archive_path: str) -> str:
    """Backward-compatible alias — returns manufacturer label."""
    return infer_manufacturer_from_archive(archive_path)


def is_bare_bin_path(path: str) -> bool:
    return os.path.splitext(path)[1].lower() == BARE_BIN_EXT


def manufacturer_match_score(manufacturer: str, entry: TopoEntry) -> int:
    """Higher score means a stronger Product Manufacturer ↔ archive match (case-insensitive)."""
    needle = _norm_manufacturer(canonical_manufacturer(manufacturer))
    if not needle:
        return 0
    hay = _norm_manufacturer(canonical_manufacturer(entry.manufacturer))
    if not hay or hay == _norm_manufacturer(_UNKNOWN_MANUFACTURER):
        return 0
    if needle == hay:
        return 200
    if needle in hay or hay in needle:
        return 150
    if len(needle) >= 4 and (hay.startswith(needle[:4]) or needle.startswith(hay[:4])):
        return 80
    return 0


def _safe_cache_name(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", (text or "").strip()) or "unknown"


def _make_entry_id(archive_path: str, inner_path: str) -> str:
    raw = f"{archive_path}|{inner_path}".encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:16]


def _bin_stem(inner_path: str) -> Optional[str]:
    name = inner_path.replace("\\", "/").rstrip("/").split("/")[-1]
    if not name.lower().endswith(".bin"):
        return None
    stem = os.path.splitext(name)[0].strip()
    return stem or None


def _is_skipped_path(inner_path: str) -> bool:
    norm = inner_path.replace("\\", "/").lower()
    return _MACOSX_MARK in norm or norm.endswith("/")


def _find_7z_exe() -> Optional[str]:
    env = os.environ.get("FRUTOOL_7Z", "").strip()
    if env and os.path.isfile(env):
        return env
    for candidate in (
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ):
        if os.path.isfile(candidate):
            return candidate
    which = shutil.which("7z")
    return which if which and os.path.isfile(which) else None


def _configure_rarfile_tool() -> bool:
    try:
        import rarfile
    except ImportError:
        return False
    if rarfile.UNRAR_TOOL and os.path.isfile(rarfile.UNRAR_TOOL):
        return True
    for candidate in (
        os.environ.get("FRUTOOL_UNRAR", "").strip(),
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files\WinRAR\Rar.exe",
    ):
        if candidate and os.path.isfile(candidate):
            rarfile.UNRAR_TOOL = candidate
            return True
    seven_zip = _find_7z_exe()
    if seven_zip:
        rarfile.UNRAR_TOOL = seven_zip
        return True
    return False


def _list_bins_zip(archive_path: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    with zipfile.ZipFile(archive_path) as zf:
        for name in zf.namelist():
            if _is_skipped_path(name):
                continue
            stem = _bin_stem(name)
            if stem:
                out.append((name, stem))
    return out


def _list_bins_7z(archive_path: str) -> list[tuple[str, str]]:
    try:
        import py7zr
    except ImportError:
        return _list_bins_seven_zip_cli(archive_path)
    out: list[tuple[str, str]] = []
    with py7zr.SevenZipFile(archive_path, mode="r") as zf:
        for name in zf.getnames():
            if _is_skipped_path(name):
                continue
            stem = _bin_stem(name)
            if stem:
                out.append((name, stem))
    return out


def _list_bins_rar(archive_path: str) -> list[tuple[str, str]]:
    if _configure_rarfile_tool():
        try:
            import rarfile

            out: list[tuple[str, str]] = []
            with rarfile.RarFile(archive_path) as rf:
                for info in rf.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename
                    if _is_skipped_path(name):
                        continue
                    stem = _bin_stem(name)
                    if stem:
                        out.append((name, stem))
            if out:
                return out
        except Exception:
            pass
    return _list_bins_seven_zip_cli(archive_path)


def _list_bins_seven_zip_cli(archive_path: str) -> list[tuple[str, str]]:
    seven_zip = _find_7z_exe()
    if not seven_zip:
        return []
    proc = subprocess.run(
        [seven_zip, "l", "-ba", archive_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        return []
    out: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) < 6:
            continue
        name = " ".join(parts[5:])
        if _is_skipped_path(name):
            continue
        stem = _bin_stem(name)
        if stem:
            out.append((name, stem))
    return out


def list_bins_in_archive(archive_path: str) -> list[tuple[str, str]]:
    if is_bare_bin_path(archive_path):
        stem = _bin_stem(os.path.basename(archive_path))
        if not stem:
            return []
        return [(os.path.basename(archive_path), stem)]
    ext = os.path.splitext(archive_path)[1].lower()
    if ext == ".zip":
        return _list_bins_zip(archive_path)
    if ext == ".7z":
        return _list_bins_7z(archive_path)
    if ext == ".rar":
        return _list_bins_rar(archive_path)
    return []


def _extract_zip_member(archive_path: str, inner_path: str, dest_file: str) -> bool:
    with zipfile.ZipFile(archive_path) as zf:
        try:
            with zf.open(inner_path) as src, open(dest_file, "wb") as dst:
                shutil.copyfileobj(src, dst)
            return True
        except KeyError:
            return False


def _extract_7z_member(archive_path: str, inner_path: str, dest_file: str) -> bool:
    try:
        import py7zr
    except ImportError:
        return _extract_seven_zip_cli(archive_path, inner_path, dest_file)
    dest_dir = os.path.dirname(dest_file)
    os.makedirs(dest_dir, exist_ok=True)
    with py7zr.SevenZipFile(archive_path, mode="r") as zf:
        try:
            zf.extract(path=dest_dir, targets=[inner_path])
        except Exception:
            return _extract_seven_zip_cli(archive_path, inner_path, dest_file)
    extracted = os.path.join(dest_dir, inner_path.replace("\\", os.sep))
    if not os.path.isfile(extracted):
        extracted = os.path.join(dest_dir, os.path.basename(inner_path))
    if not os.path.isfile(extracted):
        return False
    if os.path.abspath(extracted) != os.path.abspath(dest_file):
        shutil.move(extracted, dest_file)
    return os.path.isfile(dest_file)


def _extract_rar_member(archive_path: str, inner_path: str, dest_file: str) -> bool:
    if _configure_rarfile_tool():
        try:
            import rarfile

            dest_dir = os.path.dirname(dest_file)
            os.makedirs(dest_dir, exist_ok=True)
            with rarfile.RarFile(archive_path) as rf:
                rf.extract(inner_path, path=dest_dir)
            extracted = os.path.join(dest_dir, inner_path.replace("\\", os.sep))
            if not os.path.isfile(extracted):
                extracted = os.path.join(dest_dir, os.path.basename(inner_path))
            if os.path.isfile(extracted) and os.path.abspath(extracted) != os.path.abspath(dest_file):
                shutil.move(extracted, dest_file)
            return os.path.isfile(dest_file)
        except Exception:
            pass
    return _extract_seven_zip_cli(archive_path, inner_path, dest_file)


def _extract_seven_zip_cli(archive_path: str, inner_path: str, dest_file: str) -> bool:
    seven_zip = _find_7z_exe()
    if not seven_zip:
        return False
    dest_dir = os.path.dirname(dest_file)
    os.makedirs(dest_dir, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="frutool_topo_") as tmp:
        proc = subprocess.run(
            [seven_zip, "e", archive_path, f"-o{tmp}", inner_path, "-y"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            return False
        extracted = os.path.join(tmp, os.path.basename(inner_path))
        if not os.path.isfile(extracted):
            return False
        shutil.copy2(extracted, dest_file)
    return os.path.isfile(dest_file)


def extract_bin_member(archive_path: str, inner_path: str, dest_file: str) -> bool:
    if is_bare_bin_path(archive_path):
        if not os.path.isfile(archive_path):
            return False
        expected = os.path.basename((inner_path or archive_path).replace("\\", "/"))
        if expected and expected.casefold() != os.path.basename(archive_path).casefold():
            return False
        try:
            os.makedirs(os.path.dirname(dest_file) or ".", exist_ok=True)
            shutil.copy2(archive_path, dest_file)
            return os.path.isfile(dest_file)
        except OSError:
            return False
    ext = os.path.splitext(archive_path)[1].lower()
    if ext == ".zip":
        return _extract_zip_member(archive_path, inner_path, dest_file)
    if ext == ".7z":
        return _extract_7z_member(archive_path, inner_path, dest_file)
    if ext == ".rar":
        return _extract_rar_member(archive_path, inner_path, dest_file)
    return False


def _archive_sha256(archive_path: str) -> str:
    digest = hashlib.sha256()
    with open(archive_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive_member_paths(archive_path: str) -> set[str]:
    return {inner.replace("\\", "/") for inner, _ in list_bins_in_archive(archive_path)}


def archive_contains_member(archive_path: str, inner_path: str) -> bool:
    if not os.path.isfile(archive_path):
        return False
    normalized = inner_path.replace("\\", "/")
    return normalized in _archive_member_paths(archive_path)


def _remove_file_quiet(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _purge_suite_cache(suite_code: str) -> None:
    """Remove extracted .bin cache files for a suite code (all manufacturer/platform folders)."""
    suite_name = _safe_cache_name(suite_code)
    if not suite_name or not os.path.isdir(TOPO_CACHE_DIR):
        return
    for mfr_dir in os.listdir(TOPO_CACHE_DIR):
        mfr_path = os.path.join(TOPO_CACHE_DIR, mfr_dir)
        if not os.path.isdir(mfr_path):
            continue
        for platform_dir in os.listdir(mfr_path):
            platform_path = os.path.join(mfr_path, platform_dir)
            if not os.path.isdir(platform_path):
                continue
            _remove_file_quiet(os.path.join(platform_path, f"{suite_name}.bin"))


def cache_path_for_entry(entry: TopoEntry) -> str:
    mfr_dir = _safe_cache_name(entry.manufacturer)
    platform_part = _safe_cache_name(entry.platform) if entry.platform else "common"
    suite_name = _safe_cache_name(entry.suite_code)
    return os.path.join(TOPO_CACHE_DIR, mfr_dir, platform_part, f"{suite_name}.bin")


def extract_entry(entry: TopoEntry) -> Optional[str]:
    if not archive_contains_member(entry.archive_path, entry.inner_path):
        dest = cache_path_for_entry(entry)
        _remove_file_quiet(dest)
        return None
    dest = cache_path_for_entry(entry)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not extract_bin_member(entry.archive_path, entry.inner_path, dest):
        _remove_file_quiet(dest)
        return None
    if not os.path.isfile(dest) or os.path.getsize(dest) <= 0:
        _remove_file_quiet(dest)
        return None
    if os.path.getsize(dest) > 512:
        _remove_file_quiet(dest)
        return None
    return os.path.normpath(dest)


def _pcle_signature(dirs: list[str]) -> list[dict[str, object]]:
    sig: list[dict[str, object]] = []
    for directory in dirs:
        for path in _iter_pcle_resource_files(directory):
            name = os.path.relpath(path, directory).replace("\\", "/")
            try:
                st = os.stat(path)
            except OSError:
                continue
            sig.append(
                {
                    "dir": directory,
                    "name": name,
                    "mtime": st.st_mtime,
                    "size": st.st_size,
                    "sha256": _archive_sha256(path),
                }
            )
    sig.sort(key=lambda row: (str(row["dir"]), str(row["name"])))
    return sig


def _iter_pcle_resource_files(directory: str) -> list[str]:
    """Archives at any depth under PCLE, plus bare .bin files (recursive)."""
    found: list[str] = []
    try:
        for root, dirnames, filenames in os.walk(directory):
            dirnames[:] = [
                d for d in dirnames if _MACOSX_MARK not in d.casefold()
            ]
            for name in filenames:
                if _MACOSX_MARK in name.casefold():
                    continue
                ext = os.path.splitext(name)[1].lower()
                if ext not in ARCHIVE_EXTS and ext != BARE_BIN_EXT:
                    continue
                path = os.path.join(root, name)
                if os.path.isfile(path):
                    found.append(path)
    except OSError:
        return []
    return found


def _entry_to_row(entry: TopoEntry) -> dict[str, object]:
    return {
        "suite_code": entry.suite_code,
        "manufacturer": entry.manufacturer,
        "platform": entry.platform,
        "archive_path": entry.archive_path,
        "inner_path": entry.inner_path,
        "archive_mtime": entry.archive_mtime,
        "entry_id": entry.entry_id,
    }


def _row_to_entry(row: dict[str, object]) -> TopoEntry:
    archive_path = str(row["archive_path"])
    if "manufacturer" in row:
        manufacturer = canonical_manufacturer(str(row.get("manufacturer") or "")) or _UNKNOWN_MANUFACTURER
        platform = str(row.get("platform") or "")
    else:
        manufacturer = infer_manufacturer_from_archive(archive_path)
        platform = infer_platform_from_archive(archive_path)
    return TopoEntry(
        suite_code=str(row["suite_code"]),
        manufacturer=manufacturer,
        platform=platform,
        archive_path=archive_path,
        inner_path=str(row["inner_path"]),
        archive_mtime=float(row["archive_mtime"]),
        entry_id=str(row.get("entry_id") or _make_entry_id(archive_path, str(row["inner_path"]))),
    )


def _load_cached_index(signature: list[dict[str, object]]) -> Optional[dict[str, list[TopoEntry]]]:
    if not os.path.isfile(TOPO_INDEX_JSON):
        return None
    try:
        with open(TOPO_INDEX_JSON, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("version") != _INDEX_VERSION:
        return None
    if payload.get("signature") != signature:
        return None
    index: dict[str, list[TopoEntry]] = {}
    for suite_code, rows in (payload.get("entries") or {}).items():
        index[suite_code] = [_row_to_entry(row) for row in rows]
    return index


def _save_cached_index(signature: list[dict[str, object]], index: dict[str, list[TopoEntry]]) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    payload = {
        "version": _INDEX_VERSION,
        "signature": signature,
        "entries": {
            code: [_entry_to_row(entry) for entry in entries]
            for code, entries in sorted(index.items())
        },
    }
    with open(TOPO_INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def build_topo_index(*, log: Optional[LogFn] = None) -> dict[str, list[TopoEntry]]:
    """Scan PCLE archives and bare .bin files; map suite code -> variants."""
    dirs = resolve_pcle_dirs()
    signature = _pcle_signature(dirs)
    cached = _load_cached_index(signature)
    if cached is not None:
        return cached

    index: dict[str, list[TopoEntry]] = {}
    seen_ids: set[str] = set()
    archive_count = 0
    bare_count = 0
    for directory in dirs:
        for resource_path in _iter_pcle_resource_files(directory):
            ext = os.path.splitext(resource_path)[1].lower()
            manufacturer = infer_manufacturer_from_archive(resource_path)
            platform = infer_platform_from_archive(resource_path)
            try:
                resource_mtime = os.stat(resource_path).st_mtime
                bins = list_bins_in_archive(resource_path)
            except Exception as exc:
                if log:
                    kind = "裸 bin" if ext == BARE_BIN_EXT else "压缩包"
                    log("warning", f"跳过拓扑{kind} {os.path.basename(resource_path)}: {exc}")
                continue
            if ext == BARE_BIN_EXT:
                bare_count += 1
            else:
                archive_count += 1
            for inner_path, stem in bins:
                entry_id = _make_entry_id(resource_path, inner_path)
                if entry_id in seen_ids:
                    continue
                seen_ids.add(entry_id)
                entry = TopoEntry(
                    suite_code=stem,
                    manufacturer=manufacturer,
                    platform=platform,
                    archive_path=resource_path,
                    inner_path=inner_path,
                    archive_mtime=resource_mtime,
                    entry_id=entry_id,
                )
                index.setdefault(stem, []).append(entry)

    _save_cached_index(signature, index)
    if log:
        total = sum(len(v) for v in index.values())
        log(
            "info",
            f"拓扑索引已更新：{len(index)} 个套餐、{total} 条记录"
            f"（压缩包 {archive_count}、裸 bin {bare_count}）",
        )
    return index


def _entries_for_suite(index: dict[str, list[TopoEntry]], suite: str) -> list[TopoEntry]:
    fold = suite.casefold()
    for code, entries in index.items():
        if code.casefold() == fold:
            return list(entries)
    return []


def _collapse_manufacturer_entries(entries: list[TopoEntry]) -> list[TopoEntry]:
    """Keep the newest archive per manufacturer + platform for the same suite."""
    winners: dict[str, TopoEntry] = {}
    for entry in entries:
        key = f"{canonical_manufacturer(entry.manufacturer).casefold()}|{entry.platform.casefold()}"
        prev = winners.get(key)
        if prev is None or entry.archive_mtime > prev.archive_mtime:
            winners[key] = entry
    return list(winners.values())


def _find_entry_by_id(index: dict[str, list[TopoEntry]], entry_id: str) -> Optional[TopoEntry]:
    for entries in index.values():
        for entry in entries:
            if entry.entry_id == entry_id:
                return entry
    return None


def list_topo_catalog(*, log: Optional[LogFn] = None) -> list[dict[str, object]]:
    """Return metadata for every indexed topology .bin (no extraction)."""
    index = build_topo_index(log=log)
    catalog: list[dict[str, object]] = []
    seen: set[str] = set()
    for suite_code in sorted(index, key=lambda s: s.casefold()):
        for entry in index[suite_code]:
            if entry.entry_id in seen:
                continue
            seen.add(entry.entry_id)
            catalog.append(
                {
                    "id": entry.entry_id,
                    "suite": entry.suite_code,
                    "manufacturer": entry.manufacturer,
                    "platform": entry.platform,
                    "archive": os.path.basename(entry.archive_path),
                    "innerPath": entry.inner_path.replace("\\", "/"),
                }
            )
    return catalog


def _candidate_dict(entry: TopoEntry, path: str, *, recommended: bool, selected: bool) -> dict[str, object]:
    return {
        "id": entry.entry_id,
        "suite": entry.suite_code,
        "manufacturer": entry.manufacturer,
        "platform": entry.platform,
        "path": path,
        "archive": os.path.basename(entry.archive_path),
        "recommended": recommended,
        "selected": selected,
    }


def match_topo_candidates(
    suite_code: str,
    manufacturer: str = "",
    *,
    log: Optional[LogFn] = None,
) -> dict[str, object]:
    """Find all manufacturer variants for a suite, preload .bin files, return card data."""
    suite = (suite_code or "").strip()
    mfr = canonical_manufacturer((manufacturer or "").strip())
    catalog = list_topo_catalog(log=log)

    if not suite:
        return {
            "ok": False,
            "path": "",
            "suite": "",
            "manufacturer": mfr,
            "candidates": [],
            "catalog": catalog,
            "message": "套餐号为空。",
        }

    if not resolve_pcle_dirs():
        return {
            "ok": False,
            "path": "",
            "suite": suite,
            "manufacturer": mfr,
            "candidates": [],
            "catalog": catalog,
            "message": "未找到 PCLE 拓扑资源目录（请将压缩包或 .bin 放入 PCLE/）。",
        }

    index = build_topo_index(log=log)
    entries = _collapse_manufacturer_entries(_entries_for_suite(index, suite))
    if not entries:
        _purge_suite_cache(suite)
        return {
            "ok": False,
            "path": "",
            "suite": suite,
            "manufacturer": mfr,
            "candidates": [],
            "catalog": catalog,
            "message": f"PCLE 中未找到套餐 {suite} 对应的拓扑 .bin。",
        }

    ranked = sorted(
        entries,
        key=lambda e: (-manufacturer_match_score(mfr, e), -e.archive_mtime),
    )
    member_cache: dict[str, set[str]] = {}
    candidates: list[dict[str, object]] = []
    first_path = ""
    for i, entry in enumerate(ranked):
        archive_path = entry.archive_path
        if archive_path not in member_cache:
            member_cache[archive_path] = _archive_member_paths(archive_path)
        inner_norm = entry.inner_path.replace("\\", "/")
        if inner_norm not in member_cache[archive_path]:
            stale_dest = cache_path_for_entry(entry)
            _remove_file_quiet(stale_dest)
            if log:
                log(
                    "warning",
                    f"索引过期：{os.path.basename(archive_path)} 中已无 {entry.suite_code}.bin，已跳过",
                )
            continue
        path = extract_entry(entry)
        if not path:
            if log:
                log("warning", f"解压失败：{entry.manufacturer} / {entry.suite_code}")
            continue
        recommended = i == 0
        selected = i == 0
        if i == 0:
            first_path = path
        candidates.append(
            _candidate_dict(entry, path, recommended=recommended, selected=selected)
        )

    if not candidates:
        _purge_suite_cache(suite)
        return {
            "ok": False,
            "path": "",
            "suite": suite,
            "manufacturer": mfr,
            "candidates": [],
            "catalog": catalog,
            "message": (
                f"PCLE 中未找到套餐 {suite} 的有效拓扑 .bin"
                f"（压缩包/裸 bin 无此文件、解压失败或缓存已失效）。"
            ),
        }

    if len(candidates) == 1:
        label = _entry_display_label(ranked[0])
        message = f"已匹配套餐 {suite}（{label}），请确认后刷写。"
    elif mfr and manufacturer_match_score(mfr, ranked[0]) > 0:
        message = (
            f"套餐 {suite} 存在 {len(candidates)} 个厂商版本；"
            f"已按 Product Manufacturer（{mfr}）推荐 {_entry_display_label(ranked[0])}，请点击卡片选择。"
        )
    else:
        message = (
            f"套餐 {suite} 存在 {len(candidates)} 个厂商版本，已全部预加载，请点击卡片选择要刷写的拓扑。"
        )

    if log:
        log("info", f"套餐 {suite}：预加载 {len(candidates)} 个拓扑候选")

    return {
        "ok": True,
        "path": first_path,
        "suite": suite,
        "manufacturer": mfr,
        "candidates": candidates,
        "catalog": catalog,
        "message": message,
    }


def extract_catalog_entry(entry_id: str, *, log: Optional[LogFn] = None) -> dict[str, object]:
    """Extract a catalog item on demand when the user picks it from the library."""
    index = build_topo_index(log=log)
    entry = _find_entry_by_id(index, entry_id)
    if entry is None:
        return {"ok": False, "path": "", "message": "未找到所选拓扑记录。"}
    path = extract_entry(entry)
    if not path:
        return {"ok": False, "path": "", "message": f"解压拓扑失败：{entry.manufacturer} / {entry.suite_code}"}
    if log:
        log("info", f"已选择拓扑库条目 {_entry_display_label(entry)} / {entry.suite_code} → {path}")
    return {
        "ok": True,
        "path": path,
        "id": entry.entry_id,
        "suite": entry.suite_code,
        "manufacturer": entry.manufacturer,
        "platform": entry.platform,
        "message": f"已加载 {_entry_display_label(entry)} / {entry.suite_code}",
    }


def _entry_display_label(entry: TopoEntry) -> str:
    if entry.platform and entry.manufacturer != _UNKNOWN_MANUFACTURER:
        return f"{entry.manufacturer} · {entry.platform}"
    return entry.manufacturer


def match_topo_for_suite(
    suite_code: str,
    manufacturer: str = "",
    *,
    log: Optional[LogFn] = None,
) -> dict[str, object]:
    """Backward-compatible single-match API (best manufacturer + newest archive)."""
    result = match_topo_candidates(suite_code, manufacturer, log=log)
    if not result.get("ok"):
        return result
    candidates = result.get("candidates") or []
    if not candidates:
        result["ok"] = False
        return result
    best = candidates[0]
    result["path"] = best.get("path", "")
    return result
