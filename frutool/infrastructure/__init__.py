"""Platform I/O, subprocess, networking, and completion helpers."""
from frutool.infrastructure.log_util import classify_log, format_log_html
from frutool.infrastructure.network import (
    NetworkChoice,
    NetworkConfig,
    derive_bmc_ip,
    enumerate_ipv4_interfaces,
    explain_unusable_host_ipv4,
    is_dhcp_usable_host_ipv4,
    make_network_config,
    prefix_to_mask,
    query_adapter_link_up,
)
from frutool.infrastructure.shell_runner import kill_process_tree, run_shell_command

__all__ = [
    "NetworkChoice",
    "NetworkConfig",
    "classify_log",
    "derive_bmc_ip",
    "enumerate_ipv4_interfaces",
    "explain_unusable_host_ipv4",
    "format_log_html",
    "is_dhcp_usable_host_ipv4",
    "kill_process_tree",
    "make_network_config",
    "prefix_to_mask",
    "query_adapter_link_up",
    "run_shell_command",
]
