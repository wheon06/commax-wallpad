import base64
import importlib.util
import socket
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from custom_components.commax_wallpad.capture import capture_connections

ROOT = Path(__file__).resolve().parents[1]


def packet(payload, seq=100):
    ip = bytearray(20)
    ip[0] = 0x45
    ip[9] = 6
    ip[12:16] = socket.inet_aton("192.0.2.2")
    ip[16:20] = socket.inet_aton("192.0.2.99")
    struct.pack_into(">H", ip, 2, 40 + len(payload))
    tcp = bytearray(20)
    struct.pack_into(">HHI", tcp, 0, 50000, 30128, seq)
    tcp[12] = 0x50
    return b"\0" * 12 + b"\x08\x00" + bytes(ip) + bytes(tcp) + payload


def pcap(packets):
    header = struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    return header + b"".join(struct.pack("<IIII", 0, 0, len(p), len(p)) + p for p in packets)


def request():
    auth = base64.b64encode(b"synthetic-user:synthetic-secret")
    return (
        b"POST http://10.9.8.7:29700 HTTP/1.1\r\nUser-Agent: gSOAP/2.7\r\nProxy-Authorization: Basic "
        + auth
        + b"\r\n\r\n"
    )


def test_capture_is_generic_and_reassembles(tmp_path):
    data = request()
    capture = tmp_path / "fixture.pcap"
    capture.write_bytes(pcap([packet(data[60:], 160), packet(data[:60], 100)]))
    found = capture_connections(capture)
    assert len(found) == 1
    assert found[0].proxy_url == "http://192.0.2.99:30128"
    assert found[0].target_url == "http://10.9.8.7:29700"
    assert found[0].proxy_password == "synthetic-secret"


def test_capture_gap_not_guessed(tmp_path):
    data = request()
    capture = tmp_path / "fixture.pcap"
    capture.write_bytes(pcap([packet(data[:60], 100), packet(data[61:], 161)]))
    assert capture_connections(capture) == []


def test_capture_cli_does_not_print_credentials(tmp_path):
    capture = tmp_path / "fixture.pcap"
    capture.write_bytes(pcap([packet(request())]))
    output = tmp_path / "connection.json"
    cmd = [sys.executable, str(ROOT / "tools/capture.py"), str(capture), "--output", str(output)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "synthetic-secret" not in result.stdout + result.stderr
    assert output.stat().st_mode & 0o777 == 0o600
    assert subprocess.run(cmd, capture_output=True).returncode == 1


def cleanup_module():
    spec = importlib.util.spec_from_file_location(
        "cleanup_test_bridge", ROOT / "tools/cleanup_test_bridge.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cleanup_preserves_other_bridges_and_settings():
    before = "default_config:\nhomekit:\n  - name: Keep Me\n    port: 21064\n  - name: COMMAX WAN Test\n    port: 21065\n    advertise_ip: 192.0.2.8\nautomation: !include automations.yaml\n"
    after, changed = cleanup_module().remove_test_bridge(before)
    assert changed
    assert "COMMAX WAN Test" not in after
    assert "Keep Me" in after
    assert "automation: !include automations.yaml" in after


def test_cleanup_single_test_bridge_removes_parent():
    after, changed = cleanup_module().remove_test_bridge(
        "default_config:\nhomekit:\n  - name: COMMAX WAN Test\n    port: 21065\n"
    )
    assert changed and after == "default_config:\n"


def test_cleanup_refuses_included_configuration():
    with pytest.raises(ValueError):
        cleanup_module().remove_test_bridge("homekit: !include bridges.yaml\n")


def test_install_backs_up_without_touching_private_data(tmp_path):
    config = tmp_path / "config"
    target = config / "custom_components/commax_wallpad"
    target.mkdir(parents=True)
    (target / "old.py").write_text("old version")
    connection = config / "commax_connection.json"
    connection.write_text("private fixture")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools/install.py"), "--config-dir", str(config)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert len(list((config / "commax_backups").glob("*.tar.gz"))) == 1
    assert (target / "manifest.json").exists()
    assert not (target / "old.py").exists()
    assert connection.read_text() == "private fixture"
