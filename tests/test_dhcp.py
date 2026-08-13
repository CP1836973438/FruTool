"""Tests for DHCP error classification helpers."""
from __future__ import annotations

import pytest

from frutool.domain.dhcp import _is_bind_permission_error, _is_udp67_in_use_error


class TestDhcpErrorClassification:
    @pytest.mark.parametrize(
        "exc,expected",
        [
            (PermissionError(), True),
            (OSError(13, "Permission denied"), True),
            (OSError(10013, "access denied"), True),
            (OSError(10048, "already in use"), False),
            (RuntimeError("access is denied"), True),
        ],
    )
    def test_bind_permission_error(self, exc, expected):
        assert _is_bind_permission_error(exc) is expected

    @pytest.mark.parametrize(
        "exc,expected",
        [
            (OSError(10048, "address already in use"), True),
            (OSError(98, "address already in use"), True),
            (RuntimeError("只允许使用一次"), True),
            (PermissionError(), False),
        ],
    )
    def test_udp67_in_use_error(self, exc, expected):
        assert _is_udp67_in_use_error(exc) is expected
