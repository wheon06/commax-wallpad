"""Shared configuration keys and conservative defaults."""

DOMAIN = "commax_wallpad"
DEFAULT_POLL_SECONDS = 30
DEFAULT_TIMEOUT_SECONDS = 10
MAX_CHANNELS = 128
MAX_CHANNEL_NUMBER = 65535
CONF_PROXY_URL = "proxy_url"
CONF_TARGET_URL = "target_url"
CONF_PROXY_USERNAME = "proxy_username"
CONF_PROXY_PASSWORD = "proxy_password"
CONNECTION_KEYS = (CONF_PROXY_URL, CONF_TARGET_URL, CONF_PROXY_USERNAME, CONF_PROXY_PASSWORD)
CONF_LIGHTS = "lights"
CONF_FANS = "fans"
CONF_POLL_SECONDS = "poll_seconds"
LEGACY_CONNECTION_FILE = "commax_connection.json"
