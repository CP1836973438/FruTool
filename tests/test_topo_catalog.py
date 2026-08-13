"""Tests for PCIe topology catalog."""
from __future__ import annotations

import os
import time
import zipfile

import frutool.domain.topo_catalog as topo_catalog
from frutool.domain.topo_catalog import (
    build_topo_index,
    extract_bin_member,
    infer_manufacturer_from_archive,
    infer_platform_from_archive,
    manufacturer_match_score,
    match_topo_candidates,
    match_topo_for_suite,
    parse_suite_code,
)


class TestParseSuiteCode:
    def test_suite_prefix(self):
        assert parse_suite_code("Suite:S62D1-I8DD2M-L") == "S62D1-I8DD2M-L"

    def test_case_insensitive_prefix(self):
        assert parse_suite_code("suite:M51M1-I9DD2M") == "M51M1-I9DD2M"

    def test_empty(self):
        assert parse_suite_code("") is None
        assert parse_suite_code("   ") is None


def _make_zip(path, inner_name: str, payload: bytes = b"\x00" * 16) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(inner_name, payload)


def _patch_pcle(monkeypatch, tmp_path):
    pcle = tmp_path / "PCLE"
    pcle.mkdir()
    cache = tmp_path / "topo_cache"
    logs = tmp_path / "logs"
    cache.mkdir()
    logs.mkdir()
    monkeypatch.setattr(topo_catalog, "resolve_pcle_dirs", lambda: [str(pcle)])
    monkeypatch.setattr(topo_catalog, "TOPO_CACHE_DIR", str(cache))
    monkeypatch.setattr(topo_catalog, "TOPO_INDEX_JSON", str(logs / "topo_index.json"))
    monkeypatch.setattr(topo_catalog, "LOG_DIR", str(logs))
    return pcle, cache


class TestArchiveNaming:
    def test_infer_manufacturer_case_insensitive(self):
        assert infer_manufacturer_from_archive("inspur-YICHUN-topo.zip") == "Inspur"
        assert infer_manufacturer_from_archive("FOXCONN-xiangyang.zip") == "FOXCONN"
        assert infer_manufacturer_from_archive("huaqin_fuzhou.7z") == "HuaQin"

    def test_canonical_manufacturer(self):
        from frutool.domain.topo_catalog import canonical_manufacturer

        assert canonical_manufacturer("inspur") == "Inspur"
        assert canonical_manufacturer("FOXCONN") == "FOXCONN"
        assert canonical_manufacturer("huaqin") == "HuaQin"

    def test_infer_manufacturer_unknown_without_vendor(self):
        assert infer_manufacturer_from_archive("YICHUN PCIE TOPO.rar") == "未知厂商"

    def test_infer_platform_case_insensitive(self):
        assert infer_platform_from_archive("Inspur-YICHUN-topo.zip") == "YICHUN"
        assert infer_platform_from_archive("FOXCONN-xiangyang-topo.zip") == "XIANGYANG"
        assert infer_platform_from_archive("Inspur-topo.zip") == ""


class TestTopoCatalog:
    def test_collapse_same_manufacturer_platform_at_match_time(self, monkeypatch, tmp_path):
        pcle, _cache = _patch_pcle(monkeypatch, tmp_path)

        old_zip = pcle / "Inspur-YICHUN-20240101.zip"
        new_zip = pcle / "Inspur-YICHUN-20250401.zip"
        _make_zip(old_zip, "pkg/M51M1-I9DD2M/M51M1-I9DD2M.bin", b"\x01" * 8)
        _make_zip(new_zip, "pkg/M51M1-I9DD2M/M51M1-I9DD2M.bin", b"\x02" * 8)
        now = time.time()
        os.utime(old_zip, (now - 100, now - 100))
        os.utime(new_zip, (now, now))

        index = build_topo_index()
        assert len(index["M51M1-I9DD2M"]) == 2
        result = match_topo_candidates("M51M1-I9DD2M")
        assert len(result["candidates"]) == 1
        assert result["candidates"][0]["manufacturer"] == "Inspur"
        assert result["candidates"][0]["platform"] == "YICHUN"
        with open(str(result["candidates"][0]["path"]), "rb") as f:
            assert f.read() == b"\x02" * 8

    def test_match_multiple_manufacturers(self, monkeypatch, tmp_path):
        pcle, _cache = _patch_pcle(monkeypatch, tmp_path)
        _make_zip(
            pcle / "Inspur-YICHUN-topo.zip",
            "S62D1-I8DD2M-L/S62D1-I8DD2M-L.bin",
            b"\xaa" * 8,
        )
        _make_zip(
            pcle / "FOXCONN-YICHUN-topo.zip",
            "S62D1-I8DD2M-L/S62D1-I8DD2M-L.bin",
            b"\xbb" * 8,
        )

        result = match_topo_candidates("S62D1-I8DD2M-L", "Inspur")
        assert result["ok"] is True
        candidates = result["candidates"]
        assert len(candidates) == 2
        assert candidates[0]["manufacturer"] == "Inspur"
        assert candidates[0]["platform"] == "YICHUN"
        assert candidates[0]["recommended"] is True
        assert candidates[0]["selected"] is True

    def test_match_extracts_bin(self, monkeypatch, tmp_path):
        pcle, _cache = _patch_pcle(monkeypatch, tmp_path)
        archive = pcle / "Inspur-topo.zip"
        _make_zip(archive, "S62D1-I8DD2M-L/S62D1-I8DD2M-L.bin", b"\xab" * 32)

        result = match_topo_for_suite("S62D1-I8DD2M-L", "Inspur")
        assert result["ok"] is True
        path = str(result["path"])
        assert path.endswith("S62D1-I8DD2M-L.bin")
        with open(path, "rb") as f:
            assert f.read() == b"\xab" * 32

    def test_match_fru_manufacturer_case_insensitive(self, monkeypatch, tmp_path):
        pcle, _cache = _patch_pcle(monkeypatch, tmp_path)
        _make_zip(
            pcle / "inspur-yichun-topo.zip",
            "S62D1-I8DD2M-L/S62D1-I8DD2M-L.bin",
            b"\xaa" * 8,
        )
        result = match_topo_candidates("S62D1-I8DD2M-L", "inspur")
        assert result["ok"] is True
        assert result["candidates"][0]["manufacturer"] == "Inspur"
        assert result["candidates"][0]["recommended"] is True

    def test_manufacturer_match_score(self):
        entry = topo_catalog.TopoEntry(
            suite_code="X",
            manufacturer="Inspur",
            platform="YICHUN",
            archive_path=r"C:\PCLE\Inspur-YICHUN-topo.zip",
            inner_path="X/X.bin",
            archive_mtime=1.0,
            entry_id="abc",
        )
        assert manufacturer_match_score("Inspur", entry) >= 150
        assert manufacturer_match_score("YICHUN", entry) == 0

    def test_extract_zip_member(self, tmp_path):
        archive = tmp_path / "one.zip"
        dest = tmp_path / "out.bin"
        _make_zip(archive, "nested/X.bin", b"\xcd" * 4)
        assert extract_bin_member(str(archive), "nested/X.bin", str(dest)) is True
        assert dest.read_bytes() == b"\xcd" * 4

    def test_preload_service_parses_suite(self, monkeypatch, tmp_path):
        from frutool.presentation.services.topo_service import run_topo_preload

        called: list[tuple[str, str]] = []

        def fake_match(suite: str, manufacturer: str = "", *, log=None):
            called.append((suite, manufacturer))
            return {
                "ok": True,
                "path": str(tmp_path / "x.bin"),
                "suite": suite,
                "candidates": [],
                "catalog": [],
                "message": "ok",
            }

        monkeypatch.setattr(
            "frutool.presentation.services.topo_service.match_topo_candidates",
            fake_match,
        )
        result = run_topo_preload("Suite:S62D1-I8DD2M-L", "inspur", lambda _l, _m: None)
        assert called == [("S62D1-I8DD2M-L", "Inspur")]
        assert result["ok"] is True

    def test_catalog_returned_on_preload(self, monkeypatch, tmp_path):
        pcle, _cache = _patch_pcle(monkeypatch, tmp_path)
        _make_zip(pcle / "Inspur-A.zip", "M1/M1.bin", b"\x01")
        _make_zip(pcle / "FOXCONN-B.zip", "M2/M2.bin", b"\x02")

        result = match_topo_candidates("M1")
        assert result["ok"] is True
        catalog = result["catalog"]
        assert len(catalog) == 2
        suites = {item["suite"] for item in catalog}
        assert suites == {"M1", "M2"}

    def test_match_rejects_removed_bin_after_zip_update(self, monkeypatch, tmp_path):
        pcle, cache = _patch_pcle(monkeypatch, tmp_path)
        archive = pcle / "Inspur-topo.zip"
        _make_zip(archive, "M85M1-IADD2M-L.bin", b"\xaa" * 32)

        first = match_topo_candidates("M85M1-IADD2M-L")
        assert first["ok"] is True
        assert len(first["candidates"]) == 1
        cached_path = first["candidates"][0]["path"]
        assert os.path.isfile(cached_path)

        _make_zip(archive, "OTHER-SUITE.bin", b"\xbb" * 32)
        second = match_topo_candidates("M85M1-IADD2M-L")
        assert second["ok"] is False
        assert second["candidates"] == []
        assert not os.path.isfile(cached_path)

    def test_index_and_match_bare_bin_in_pcle_root(self, monkeypatch, tmp_path):
        pcle, _cache = _patch_pcle(monkeypatch, tmp_path)
        bare = pcle / "M51M1-I9DD2M.bin"
        bare.write_bytes(b"\x11" * 16)

        index = build_topo_index()
        assert "M51M1-I9DD2M" in index
        assert len(index["M51M1-I9DD2M"]) == 1
        assert index["M51M1-I9DD2M"][0].archive_path.endswith("M51M1-I9DD2M.bin")

        result = match_topo_candidates("M51M1-I9DD2M")
        assert result["ok"] is True
        assert len(result["candidates"]) == 1
        with open(str(result["candidates"][0]["path"]), "rb") as f:
            assert f.read() == b"\x11" * 16

    def test_bare_bin_infers_manufacturer_from_parent_folder(self, monkeypatch, tmp_path):
        pcle, _cache = _patch_pcle(monkeypatch, tmp_path)
        vendor_dir = pcle / "Inspur" / "YICHUN"
        vendor_dir.mkdir(parents=True)
        bare = vendor_dir / "S62D1-I8DD2M-L.bin"
        bare.write_bytes(b"\x22" * 8)

        result = match_topo_candidates("S62D1-I8DD2M-L", "Inspur")
        assert result["ok"] is True
        cand = result["candidates"][0]
        assert cand["manufacturer"] == "Inspur"
        assert cand["platform"] == "YICHUN"
        assert cand["archive"] == "S62D1-I8DD2M-L.bin"

    def test_bare_bin_and_archive_both_indexed(self, monkeypatch, tmp_path):
        pcle, _cache = _patch_pcle(monkeypatch, tmp_path)
        _make_zip(
            pcle / "FOXCONN-topo.zip",
            "M51M1-I9DD2M/M51M1-I9DD2M.bin",
            b"\xaa" * 8,
        )
        (pcle / "Inspur").mkdir()
        (pcle / "Inspur" / "M51M1-I9DD2M.bin").write_bytes(b"\xbb" * 8)

        result = match_topo_candidates("M51M1-I9DD2M", "Inspur")
        assert result["ok"] is True
        manufacturers = {c["manufacturer"] for c in result["candidates"]}
        assert manufacturers == {"FOXCONN", "Inspur"}
        assert result["candidates"][0]["manufacturer"] == "Inspur"
