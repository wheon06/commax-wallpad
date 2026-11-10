"""SOAP encoding/decoding for the observed COMMAX binary-light protocol."""

import xml.etree.ElementTree as ET

from .models import validate_order

SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
ENCODING = "http://schemas.xmlsoap.org/soap/encoding/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS = "urn:cds"
MAX_RESPONSE_BYTES = 262144


class CommaxError(Exception):
    """Sanitized public error; never includes request or response content."""


class AuthenticationError(CommaxError):
    """The proxy rejected credentials."""


class ConnectionError(CommaxError):
    """The transport or remote proxy failed."""


class ProtocolError(CommaxError):
    """A SOAP response is invalid, mismatched or reports a device error."""


def envelope(operation: str) -> bytes:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<SOAP-ENV:Envelope xmlns:SOAP-ENV="{SOAP}" '
        f'xmlns:SOAP-ENC="{ENCODING}" xmlns:xsi="{XSI}" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:ns="urn:cds">'
        f'<SOAP-ENV:Body SOAP-ENV:encodingStyle="{ENCODING}">'
        f"{operation}</SOAP-ENV:Body></SOAP-ENV:Envelope>"
    ).encode()


def get_request(order: int) -> bytes:
    validate_order(order)
    return envelope(f"<ns:getLightItem><order>{order}</order></ns:getLightItem>")


def set_request(order: int, on: bool) -> bytes:
    validate_order(order)
    if not isinstance(on, bool):
        raise ValueError("Power must be a boolean")
    fields = (
        "lightBinary",
        "lightDimmable",
        "lightPower-Off",
        "lightPower-On",
        "lightPower-AllOff",
        "lightPower-AllOn",
        "dimmerLevelFrom",
        "dimmerLevelTo",
    )
    properties = "".join(f"<{key}>0</{key}>" for key in fields)
    power = "lightPower-On" if on else "lightPower-Off"
    return envelope(
        '<ns:setLight><in xsi:type="ns:light"><dev>light</dev>'
        f"<proto>protoCommax</proto><intf>intfRS485</intf><order>{order}</order>"
        f"<devLightProperty>{properties}</devLightProperty>"
        "<lightZoneMainName></lightZoneMainName><lightZoneSubName></lightZoneSubName>"
        "<dimmableLevel>0</dimmableLevel><model>model-Light-JoongAngControl</model>"
        f"<lightPower>{power}</lightPower><lightSwitchMode>lightSwitch-Binary</lightSwitchMode>"
        "<lightDevError>devError-no</lightDevError><func>f-lightPower</func>"
        "</in></ns:setLight>"
    )


def parse_response(data: bytes, expected: str) -> ET.Element:
    # Decode before checking XML declarations so UTF-16 cannot bypass this check.
    if len(data) > MAX_RESPONSE_BYTES:
        raise ProtocolError("SOAP response exceeds size limit")
    try:
        text = data.decode("utf-8-sig")
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise ProtocolError("Unsupported XML declaration")
        root = ET.fromstring(text)
    except (UnicodeError, ET.ParseError):
        raise ProtocolError("Invalid UTF-8 SOAP response") from None
    if root.tag != f"{{{SOAP}}}Envelope":
        raise ProtocolError("Invalid SOAP envelope")
    body = root.find(f"{{{SOAP}}}Body")
    if body is None or len(body) != 1:
        raise ProtocolError("Invalid SOAP body")
    if body[0].tag == f"{{{SOAP}}}Fault":
        raise ProtocolError("SOAP fault returned")
    if body[0].tag != f"{{{NS}}}{expected}":
        raise ProtocolError("Unexpected SOAP response operation")
    return body[0]


def parse_light(data: bytes, order: int) -> bool:
    item = parse_response(data, "getLightItemResponse").find("return")
    if item is None or item.findtext("order") != str(order):
        raise ProtocolError("Response channel does not match request")
    if item.findtext("lightDevError") not in (None, "devError-no"):
        raise ProtocolError("Device reported an error")
    power = item.findtext("lightPower")
    if power not in ("lightPower-On", "lightPower-Off"):
        raise ProtocolError("Unknown power state")
    return power == "lightPower-On"
