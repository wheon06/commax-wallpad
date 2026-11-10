#!/usr/bin/env python3
"""Read one configured light/fan channel using only Python's standard library."""

import argparse
import base64
import http.client
import json
from pathlib import Path
from urllib.parse import urlsplit

from _bootstrap import core


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("commax_connection.json"))
    parser.add_argument("--order", type=int, required=True)
    args = parser.parse_args()
    conn = None
    try:
        models, protocol = core("models"), core("protocol")
        config = models.ConnectionConfig.from_mapping(json.loads(args.config.read_text()))
        payload = protocol.get_request(args.order)
        proxy = urlsplit(config.proxy_url)
        conn = http.client.HTTPConnection(proxy.hostname, proxy.port or 80, timeout=10)
        auth = base64.b64encode(
            f"{config.proxy_username}:{config.proxy_password}".encode()
        ).decode()
        conn.request(
            "POST",
            config.target_url,
            body=payload,
            headers={
                "Host": urlsplit(config.target_url).netloc,
                "Content-Type": "text/xml; charset=utf-8",
                "User-Agent": "gSOAP/2.7",
                "SOAPAction": '""',
                "Connection": "close",
                "Proxy-Authorization": "Basic " + auth,
            },
        )
        response = conn.getresponse()
        if response.status != 200:
            parser.exit(1, f"Read failed: HTTP {response.status}. No control command sent.\n")
        on = protocol.parse_light(response.read(protocol.MAX_RESPONSE_BYTES + 1), args.order)
        print(f"Channel {args.order}: {'ON' if on else 'OFF'}")
    except (OSError, ValueError, KeyError, TypeError, http.client.HTTPException):
        parser.exit(1, "Read failed. Check the private config file and connection.\n")
    except core("protocol").CommaxError:
        parser.exit(1, "Read failed. Invalid or unexpected SOAP status response.\n")
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
