import re
import unicodedata

DOMAIN = "goecharger"
CONF_NAME = "name"
CONF_SERIAL = "serial"
CONF_CHARGERS = "chargers"
CONF_CORRECTION_FACTOR = "correction_factor"
CONF_API_VERSION = "api_version"
CHARGER_API = "charger_api"

API_VERSION_V1 = "v1"
API_VERSION_V2 = "v2"
API_VERSION_AUTO = "auto"
DEFAULT_API_VERSION = API_VERSION_V1
API_VERSIONS = {
    API_VERSION_V1: "v1",
    API_VERSION_V2: "v2 (recommended)",
}
API_VERSION_OPTIONS = {
    API_VERSION_AUTO: "Auto-detect",
    **API_VERSIONS,
}

_INVALID_ENTITY_ID_CHARS = re.compile(r"[^a-z0-9_]+")


def _slugify(value):
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = value.encode("ascii", "ignore").decode()
    return _INVALID_ENTITY_ID_CHARS.sub("_", value).strip("_")


def charger_entity_id(domain, charger_name, attribute):
    return f"{domain}.goecharger_{_slugify(charger_name) or 'charger'}_{attribute}"
