"""Offline PCAP parsing; credentials stay on the user's machine."""

import base64
import re
import struct
from pathlib import Path

from .models import ConnectionConfig


def frames(data):
    if data[:4] == b"\x0a\x0d\x0d\x0a":
        offset, endian, links = 0, "<", []
        while offset + 12 <= len(data):
            if data[offset : offset + 4] == b"\x0a\x0d\x0d\x0a":
                bom = data[offset + 8 : offset + 12]
                endian = "<" if bom == b"\x4d\x3c\x2b\x1a" else ">"
                links = []
            # Apple's tcpdump may append an empty classic-PCAP section on exit.
            if len(data) - offset == 24 and data[offset : offset + 4] in (
                b"\xd4\xc3\xb2\xa1",
                b"\xa1\xb2\xc3\xd4",
            ):
                break
            kind, size = struct.unpack_from(endian + "II", data, offset)
            if size < 12 or size % 4 or offset + size > len(data):
                raise ValueError("Invalid PCAPNG block")
            if struct.unpack_from(endian + "I", data, offset + size - 4)[0] != size:
                raise ValueError("PCAPNG block length mismatch")
            value = data[offset + 8 : offset + size - 4]
            if kind == 1:
                if len(value) < 8:
                    raise ValueError("Truncated PCAPNG interface")
                links.append(struct.unpack_from(endian + "H", value)[0])
            elif kind == 6:
                if len(value) < 20:
                    raise ValueError("Truncated PCAPNG packet")
                interface, _, _, caplen, _ = struct.unpack_from(endian + "IIIII", value)
                if interface >= len(links) or caplen > len(value) - 20:
                    raise ValueError("Invalid PCAPNG packet length or interface")
                yield links[interface], value[20 : 20 + caplen]
            offset += size
    else:
        magic = data[:4]
        if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
            endian = "<"
        elif magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
            endian = ">"
        else:
            raise ValueError("Not a supported PCAP/PCAPNG file")
        if len(data) < 24:
            raise ValueError("Truncated PCAP header")
        link = struct.unpack_from(endian + "I", data, 20)[0] & 0xFFFF
        offset = 24
        while offset + 16 <= len(data):
            _, _, caplen, _ = struct.unpack_from(endian + "IIII", data, offset)
            if offset + 16 + caplen > len(data):
                raise ValueError("Truncated packet record")
            yield link, data[offset + 16 : offset + 16 + caplen]
            offset += 16 + caplen


def capture_connections(path: Path) -> list[ConnectionConfig]:
    """Read gSOAP requests and recover only explicit, observed proxy connections.

    Supports classic PCAP and PCAPNG; IPv4 over Ethernet, loopback, raw IP
    and Apple PKTAP. TCP fragments are reassembled only when contiguous.
    IPv6 transport and encrypted captures are not supported.
    """
    streams = {}
    for link, packet in frames(Path(path).read_bytes()):
        if link == 1:
            if len(packet) < 14:
                continue
            ether = packet[12:14]
            offset = 14
            while ether in (b"\x81\x00", b"\x88\xa8") and len(packet) >= offset + 4:
                ether = packet[offset + 2 : offset + 4]
                offset += 4
            if ether != b"\x08\x00":
                continue
            packet = packet[offset:]
        elif link == 258:
            if len(packet) < 4:
                continue
            packet = packet[struct.unpack_from("<I", packet)[0] :]
        elif link in (0, 108):
            packet = packet[4:]
        elif link != 101:
            continue
        if len(packet) < 40 or packet[0] >> 4 != 4 or packet[9] != 6:
            continue
        # Fragmented IP requires a separate reassembler; do not guess.
        if struct.unpack_from(">H", packet, 6)[0] & 0x3FFF:
            continue
        iplen = (packet[0] & 15) * 4
        total = struct.unpack_from(">H", packet, 2)[0]
        tcp = packet[iplen:total]
        if iplen < 20 or len(tcp) < 20:
            continue
        tcp_len = (tcp[12] >> 4) * 4
        if tcp_len < 20 or tcp_len > len(tcp):
            continue
        payload = tcp[tcp_len:]
        if not payload:
            continue
        sport, dport, seq = struct.unpack_from(">HHI", tcp)
        key = (packet[12:16], packet[16:20], sport, dport)
        parts = streams.setdefault(key, {})
        if seq not in parts or len(parts[seq]) < len(payload):
            parts[seq] = payload
    connections = []
    for (_, destination, _, port), parts in streams.items():
        joined = bytearray()
        end = None
        for seq, payload in sorted(parts.items()):
            if end is not None and seq > end:
                joined.extend(b"\n[GAP]\n")
            skip = max(0, (end or seq) - seq)
            joined.extend(payload[skip:])
            end = max(end or seq, seq + len(payload))
        data = bytes(joined)
        for match in re.finditer(
            rb"POST (http://[^ \r\n]+) HTTP/1\.[01]\r\n(.*?)\r\n\r\n", data, re.S
        ):
            headers = match.group(2)
            if b"gSOAP/" not in headers or b"[GAP]" in headers:
                continue
            auth = re.search(rb"(?im)^Proxy-Authorization:\s*Basic\s+([^\r\n ]+)", headers)
            if auth is None:
                continue
            try:
                username, password = (
                    base64.b64decode(auth.group(1), validate=True).decode().split(":", 1)
                )
                proxy_host = ".".join(str(x) for x in destination)
                config = ConnectionConfig.from_mapping(
                    {
                        "proxy_url": f"http://{proxy_host}:{port}",
                        "target_url": match.group(1).decode("ascii"),
                        "proxy_username": username,
                        "proxy_password": password,
                    }
                )
            except (UnicodeError, ValueError, KeyError):
                continue
            if config not in connections:
                connections.append(config)
    return connections
