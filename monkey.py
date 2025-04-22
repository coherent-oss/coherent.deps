import functools
import logging
import platform
import subprocess
import sys

import dns.resolver


def get_active_windows_dns_servers():
    """
    Uses PowerShell to get a set of DNS Server IPs from active IPv4 interfaces.
    """
    return set(map(get_dns, get_interface_indexes()))


def non_empty_lines(lines):
    return filter(None, (line.strip() for line in lines))


def get_interface_indexes():
    # Get InterfaceIndex of active, physical, IPv4-enabled adapters
    ps_command_get_indexes = (
        "Get-NetAdapter -OperationalStatus Up -AddressFamily IPv4 -Physical | "
        "Select-Object -ExpandProperty InterfaceIndex"
    )
    result_indexes = subprocess.run(
        ["powershell", "-Command", ps_command_get_indexes],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    return map(int, non_empty_lines(result_indexes.stdout).splitlines())


def get_dns(index):
    """
    Process the index to get DNS servers for that interface.
    """
    index_int = int(index.strip())
    ps_command_get_dns = (
        f"Get-DnsClientServerAddress -InterfaceIndex {index_int} -AddressFamily IPv4 | "
        "Select-Object -ExpandProperty ServerAddresses"
    )
    result_dns = subprocess.run(
        ["powershell", "-Command", ps_command_get_dns],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,  # check=False as it errors if no servers are set
    )
    # Add servers to the set (handles potential multiple servers per adapter)
    if result_dns.returncode != 0:
        return

    return non_empty_lines(result_dns.stdout)


def patch_dnspython_resolver_config():
    """
    Applies the monkeypatch to dns.resolver.Resolver._config_resolver
    to filter nameservers based on active Windows interfaces.

    Workaround for coherent-oss/coherent.deps#15.
    """
    if platform.system() != "Windows":
        return

    resolver = dns.resolver.get_default_resolver()

    original_servers = resolver.nameservers

    # Get DNS servers currently configured on *active* interfaces
    active_servers_set = get_active_windows_dns_servers()

    matching_servers = active_servers_set.intersection(original_servers)

    if not matching_servers:
        # Keep the original list if no active servers found
        return

    resolver.nameservers = matching_servers
