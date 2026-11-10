# COMMAX Wallpad

Unofficial Home Assistant integration for binary lights and exhaust fans using COMMAX's observed gSOAP/HTTP-forward-proxy protocol. Apple Home control is scoped to the local home network. The wallpad connection itself may still rely on the installation's remote proxy.

The original 0.1 implementation was tested on one CDP-1020DW installation. Version 0.2 uses async HTTP and has automated Home Assistant tests; hardware upgrade verification is still required. Other models and installations are not automatically supported.

## Install

After publication, add `https://github.com/wheon06/commax-wallpad` as a custom **Integration** repository in HACS, download it and restart HA. This does not imply inclusion in HACS's default catalog.

Alternatively, unpack the source and run:

```sh
python3 tools/install.py --config-dir /YOUR/HA/CONFIG
```

Existing component files are backed up. Restart HA, then add **COMMAX Wallpad** through Devices & services. Enter endpoints and proxy credentials from your own app traffic, or import an existing `/config/commax_connection.json`. Credentials are not included in this repository.

## Channel types

Enter light/fan channel numbers or short ranges, for example lights `1-3,6` and fans `7,8`. Only explicitly configured channels are used. Change these lists in the integration options later to reclassify a channel. Moving a number to fans removes its old light entity and creates a fan entity. Reload HomeKit Bridge afterwards; Apple Home room and automation assignments for that channel may need to be updated.

Create one HomeKit Bridge, include the intended light/fan entities and pair an iPhone on the same LAN. No port forwarding is part of this project's installation.

## Tools and tests

- `tools/capture.py`: offline extraction from your own plaintext IPv4 PCAP/PCAPNG; no credentials printed.
- `tools/check.py`: read-only status query for one explicit channel.
- `tools/install.py`: installation with a backup of the previous component.
- `tools/cleanup_test_bridge.py`: dry-run by default; only the named development test bridge is eligible.
- `tools/build.py`: allowlisted HACS/source archives.

Development uses Python 3.14, `requirements-dev.txt`, pytest and Ruff. Tests use synthetic data and loopback servers only.

[Full Korean guide](README.md) · [Reinstallation](docs/reinstall.md) · [Security](SECURITY.md) · MIT license
