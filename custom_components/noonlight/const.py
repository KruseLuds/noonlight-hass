"""Constants for the Noonlight Home Assistant integration."""

from homeassistant.const import Platform
from noonlight import (
    NOONLIGHT_SERVICES_FIRE,
    NOONLIGHT_SERVICES_MEDICAL,
    NOONLIGHT_SERVICES_POLICE,
)

# Integration version shown/used by this fork.
VERSION = "v1.2.0"

# Home Assistant integration domain.
DOMAIN = "noonlight"

# Platforms created by this integration.
PLATFORMS = [Platform.SWITCH]

# Default integration identity and endpoint values.
DEFAULT_NAME = "Noonlight"
DEFAULT_API_ENDPOINT = "https://api.noonlight.com/platform/v1"
DEFAULT_TOKEN_ENDPOINT = "https://noonlight.konnected.io/ha/token"

# Config entry / YAML configuration keys.
CONF_SECRET = "secret"
CONF_API_ENDPOINT = "api_endpoint"
CONF_TOKEN_ENDPOINT = "token_endpoint"
CONF_ADDRESS_LINE1 = "address1"
CONF_ADDRESS_LINE2 = "address2"
CONF_CITY = "city"
CONF_STATE = "state"
CONF_ZIP = "zip"
CONF_LOCATION_MODE = "location_mode"

# Noonlight alarm statuses used by the integration.
CONST_ALARM_STATUS_ACTIVE = "ACTIVE"
CONST_ALARM_STATUS_CANCELED = "CANCELED"

# Home Assistant service name registered as noonlight.create_alarm.
CONST_NOONLIGHT_HA_SERVICE_CREATE_ALARM = "create_alarm"

# Service types accepted by Noonlight alarm creation.
CONST_NOONLIGHT_SERVICE_TYPES = (
    NOONLIGHT_SERVICES_POLICE,
    NOONLIGHT_SERVICES_FIRE,
    NOONLIGHT_SERVICES_MEDICAL,
)

# Dispatcher/event names used by switches and automations.
EVENT_NOONLIGHT_TOKEN_REFRESHED = "noonlight_token_refreshed"
EVENT_NOONLIGHT_ALARM_CANCELED = "noonlight_alarm_canceled"
EVENT_NOONLIGHT_ALARM_CREATED = "noonlight_alarm_created"

# Persistent notification IDs.
NOTIFICATION_TOKEN_UPDATE_FAILURE = "noonlight_token_update_failure"
NOTIFICATION_TOKEN_UPDATE_SUCCESS = "noonlight_token_update_success"
NOTIFICATION_ALARM_CREATE_FAILURE = "noonlight_alarm_create_failure"

# Dispatch contact and operator instruction configuration keys.
CONF_NAME = "name"
CONF_PHONE = "phone"
CONF_NAME2 = "name2"
CONF_PHONE2 = "phone2"
CONF_INSTRUCTIONS = "instructions"

# Optional developer token field retained for compatibility with older flows.
CONF_DEV_TOKEN = "dev_token"

# Service-call attributes added by this fork.
#
# alarm_cause:
#   Human-readable cause for the alarm, usually the triggering sensor text.
#
# instructions:
#   Runtime operator instructions. These override/fill in dispatch instructions
#   for a specific alarm request without changing the saved config entry.
ATTR_ALARM_CAUSE = "alarm_cause"
ATTR_INSTRUCTIONS = "instructions"