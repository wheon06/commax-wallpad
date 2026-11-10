import pytest

from custom_components.commax_wallpad.models import (
    ConnectionConfig,
    parse_orders,
    validate_channels,
)
from custom_components.commax_wallpad.protocol import (
    ProtocolError,
    envelope,
    get_request,
    parse_light,
    parse_response,
    set_request,
)

from .conftest import CONNECTION


def state_reply(order=6, power="lightPower-On", error="devError-no"):
    return envelope(
        f"<ns:getLightItemResponse><return><order>{order}</order>"
        f"<lightPower>{power}</lightPower><lightDevError>{error}</lightDevError>"
        "</return></ns:getLightItemResponse>"
    )


@pytest.mark.parametrize(
    "value,expected", [("1-3,6", [1, 2, 3, 6]), ("", []), (" 19, 25 ", [19, 25])]
)
def test_channel_lists(value, expected):
    assert parse_orders(value) == expected


@pytest.mark.parametrize("value", ["0", "-1", "1,1", "3-1", "1-129", "65536", "six", "1-2,2"])
def test_invalid_channels(value):
    with pytest.raises(ValueError):
        parse_orders(value)


def test_overlapping_types():
    with pytest.raises(ValueError):
        validate_channels("1,6", "6")
    with pytest.raises(ValueError):
        validate_channels("", "")


@pytest.mark.parametrize(
    "key,value",
    [
        ("proxy_url", "http://user:password@example.test"),
        ("proxy_url", "http://example.test/path"),
        ("target_url", "http://example.test:0"),
        ("target_url", "http://example.test/#fragment"),
        ("target_url", "http://example.test/\r\nX: test"),
        ("proxy_username", "user:colon"),
        ("proxy_password", ""),
    ],
)
def test_invalid_connection(key, value):
    with pytest.raises(ValueError):
        ConnectionConfig.from_mapping({**CONNECTION, key: value})


def test_config_repr_is_private():
    config = ConnectionConfig.from_mapping(CONNECTION)
    assert config.proxy_password not in repr(config)
    assert config.proxy_username not in repr(config)
    assert "192.0.2.10" not in repr(config)


def test_only_explicit_channel_is_encoded():
    assert b"<order>6</order>" in get_request(6)
    assert b"setLight" not in get_request(6)
    assert b"<lightPower>lightPower-Off</lightPower>" in set_request(15, False)
    with pytest.raises(ValueError):
        set_request(6, "on")


@pytest.mark.parametrize("power,expected", [("lightPower-On", True), ("lightPower-Off", False)])
def test_state(power, expected):
    assert parse_light(state_reply(power=power), 6) is expected


@pytest.mark.parametrize(
    "reply",
    [
        state_reply(order=15),
        state_reply(power="unknown"),
        state_reply(error="devError-yes"),
        b"not XML",
        b"<!DOCTYPE x [<!ENTITY y 'secret'>]><x/>",
        "<?xml version='1.0' encoding='utf-16'?><x/>".encode("utf-16"),
        envelope("<SOAP-ENV:Fault><faultstring>sensitive</faultstring></SOAP-ENV:Fault>"),
    ],
)
def test_reject_bad_response(reply):
    with pytest.raises(ProtocolError) as caught:
        parse_light(reply, 6)
    assert "sensitive" not in str(caught.value)


def test_response_size_limit():
    with pytest.raises(ProtocolError):
        parse_response(b"x" * 262145, "getLightItemResponse")
