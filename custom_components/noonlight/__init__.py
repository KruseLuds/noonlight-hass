"""Noonlight integration for Home Assistant.

This module contains the runtime portion of the Noonlight integration.
It is responsible for:

- importing YAML configuration into a config entry
- registering the ``noonlight.create_alarm`` Home Assistant service
- registering the Noonlight webhook endpoint
- renewing Noonlight access tokens on demand
- creating Noonlight alarm dispatch requests
- firing Home Assistant events that make dispatch attempts observable

This fork intentionally adds runtime endpoint selection and additional event
visibility so Home Assistant automations can safely route between sandbox and
production behavior without changing integration configuration each time.

Token renewal design:

The integration does not perform background token refreshes while idle. Tokens
are renewed on demand immediately before creating an alarm. This avoids
unnecessary token endpoint traffic and ensures the token endpoint used for a
dispatch matches the runtime endpoint selected by the Home Assistant service
call.
"""

import logging
from datetime import timedelta

from aiohttp import web

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, CONF_LATITUDE, CONF_LONGITUDE, CONF_PIN
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType

import noonlight as nl

from .const import (
    CONF_ADDRESS_LINE1,
    CONF_ADDRESS_LINE2,
    CONF_API_ENDPOINT,
    CONF_CITY,
    CONF_DEV_TOKEN,
    CONF_INSTRUCTIONS,
    CONF_NAME,
    CONF_NAME2,
    CONF_PHONE,
    CONF_PHONE2,
    CONF_SECRET,
    CONF_STATE,
    CONF_TOKEN_ENDPOINT,
    CONF_ZIP,
    ATTR_ALARM_CAUSE,
    ATTR_INSTRUCTIONS,
    CONST_ALARM_STATUS_ACTIVE,
    CONST_NOONLIGHT_HA_SERVICE_CREATE_ALARM,
    CONST_NOONLIGHT_SERVICE_TYPES,
    DOMAIN,
    EVENT_NOONLIGHT_ALARM_CREATED,
    EVENT_NOONLIGHT_TOKEN_REFRESHED,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

# Home Assistant event names used for observability and fallback automations.
# These events are intentionally separate from dispatcher signals so YAML
# automations can listen for dispatch lifecycle events directly.
EVENT_NOONLIGHT_ALARM_ATTEMPTED = "noonlight_alarm_attempted"
EVENT_NOONLIGHT_ALARM_FAILED = "noonlight_alarm_failed"
EVENT_NOONLIGHT_WEBHOOK_RECEIVED = "noonlight_webhook_received"

# Stable webhook ID registered with Home Assistant for Noonlight dispatch events.
WEBHOOK_ID = "noonlight_dispatch_events"


# YAML configuration schema retained for import/backward compatibility. Newer
# Home Assistant integrations prefer config entries, so async_setup imports YAML
# config into a config entry and raises a deprecation repair warning.
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ID): cv.string,
                vol.Required(CONF_SECRET): cv.string,
                vol.Required(CONF_API_ENDPOINT): cv.string,
                vol.Required(CONF_TOKEN_ENDPOINT): cv.string,
                vol.Optional(CONF_ADDRESS_LINE1): cv.string,
                vol.Optional(CONF_ADDRESS_LINE2): cv.string,
                vol.Optional(CONF_CITY): cv.string,
                vol.Optional(CONF_STATE): cv.string,
                vol.Optional(CONF_ZIP): cv.string,
                vol.Optional(CONF_NAME): cv.string,
                vol.Optional(CONF_PHONE): cv.string,
                vol.Optional(CONF_PIN): cv.string,
                vol.Optional(CONF_NAME2): cv.string,
                vol.Optional(CONF_PHONE2): cv.string,
                vol.Optional(CONF_INSTRUCTIONS): cv.string,
                vol.Inclusive(
                    CONF_LATITUDE, "coordinates", "Include both latitude and longitude"
                ): cv.latitude,
                vol.Inclusive(
                    CONF_LONGITUDE, "coordinates", "Include both latitude and longitude"
                ): cv.longitude,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML and import the YAML config into a config entry.

    Home Assistant is moving away from YAML setup for integrations. This path
    is kept so existing installations can still start, while Home Assistant is
    also asked to create/import a config entry from the YAML values.
    """
    if DOMAIN not in config:
        return True

    _LOGGER.debug("[async_setup] config: %s", config[DOMAIN])

    # Inform the user that YAML setup is deprecated. The integration continues
    # to work, but users should eventually migrate to config-entry setup.
    async_create_issue(
        hass,
        HOMEASSISTANT_DOMAIN,
        f"deprecated_yaml_{DOMAIN}",
        breaks_in_ha_version="2025.1",
        is_fixable=False,
        is_persistent=False,
        issue_domain=DOMAIN,
        severity=IssueSeverity.WARNING,
        translation_key="deprecated_yaml",
        translation_placeholders={
            "domain": DOMAIN,
            "integration_title": "Noonlight",
        },
    )

    # Import YAML configuration asynchronously into Home Assistant's config
    # entry flow. This preserves older configuration while aligning with the
    # modern Home Assistant setup model.
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Noonlight integration from a config entry.

    This creates the integration runtime object, registers Home Assistant
    services, registers the webhook handler, and loads the integration
    platforms.

    This fork intentionally does not schedule background token renewal. The
    ``create_alarm`` flow force-renews the token immediately before dispatch,
    using the token endpoint chosen by that service call.
    """

    _LOGGER.debug("[init async_setup_entry] entry: %s", entry.data)
    noonlight_integration = NoonlightIntegration(hass, entry.data)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = noonlight_integration

    async def handle_create_alarm_service(call):
        """Create a Noonlight alarm from a Home Assistant service call.

        This is the Home Assistant service entry point for automations/scripts:
        ``noonlight.create_alarm``.

        The endpoint and token override fields allow a caller to route a single
        dispatch attempt to sandbox or production without changing the saved
        integration configuration. The server token override is used for the
        Noonlight sandbox dispatch endpoint only.
        """
        service = call.data.get("service", None)
        alarm_cause = call.data.get(ATTR_ALARM_CAUSE)
        instructions = call.data.get(ATTR_INSTRUCTIONS)
        api_endpoint_override = call.data.get("api_endpoint_override")
        token_endpoint_override = call.data.get("token_endpoint_override")
        server_token_override = call.data.get("server_token_override")

        await noonlight_integration.create_alarm(
            alarm_types=[service],
            alarm_cause=alarm_cause,
            instructions=instructions,
            api_endpoint_override=api_endpoint_override,
            token_endpoint_override=token_endpoint_override,
            server_token_override=server_token_override,
        )

    hass.services.async_register(
        DOMAIN, CONST_NOONLIGHT_HA_SERVICE_CREATE_ALARM, handle_create_alarm_service
    )

    async def handle_noonlight_webhook(hass, webhook_id, request):
        """Receive Noonlight webhook events and forward them to Home Assistant.

        Noonlight may send dispatch status callbacks. The integration does not
        try to interpret every possible payload here. Instead, it fires a Home
        Assistant event containing the raw payload so YAML automations can log,
        notify, or inspect it without requiring a code change for each payload
        shape.
        """
        try:
            payload = await request.json()
        except Exception:
            # If the webhook body is not valid JSON, preserve the raw body so
            # troubleshooting still has the original inbound content.
            payload = {"raw_body": await request.text()}

        event_data = {
            "webhook_id": webhook_id,
            "payload": payload,
            "remote": request.remote,
        }

        _LOGGER.info("Noonlight webhook received: %s", event_data)
        hass.bus.async_fire(EVENT_NOONLIGHT_WEBHOOK_RECEIVED, event_data)

        return web.Response(text="OK", status=200)

    webhook.async_register(
        hass,
        DOMAIN,
        "Noonlight Dispatch Events",
        WEBHOOK_ID,
        handle_noonlight_webhook,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the Noonlight config entry and unregister runtime resources."""
    _LOGGER.info("Unloading: %s", entry.data)

    webhook.async_unregister(hass, WEBHOOK_ID)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)

    return unload_ok


class NoonlightException(HomeAssistantError):
    """General exception for Noonlight integration failures."""

    pass


class NoonlightIntegration:
    """Runtime helper for communicating with Noonlight.

    The object owns the aiohttp session, Noonlight client, token state, and
    current alarm object. It also centralizes the custom endpoint override and
    Home Assistant event behavior used by this fork.
    """

    def __init__(self, hass, conf):
        """Initialize the Noonlight runtime wrapper."""
        self.hass = hass
        self.config = conf

        # Raw token response from the token broker/endpoint. The response is
        # normalized by _set_token_response so the expires value is a datetime.
        self._access_token_response = {}

        # Last alarm object returned by the Noonlight client. This is used for
        # status checks and for adding a secondary person on dispatch alarms.
        self._alarm = None

        # Renew when less than two hours remain if a caller uses non-forced
        # token checking. Dispatch calls force renewal before creating an alarm.
        self._time_to_renew = timedelta(hours=2)
        self._websession = async_get_clientsession(self.hass)
        self.client = nl.NoonlightClient(
            token=self.access_token, session=self._websession
        )
        self.client.set_base_url(self.config[CONF_API_ENDPOINT])

        # Store address components once for payload construction. The dispatch
        # endpoint uses the address-based payload, while the older/default flow
        # can fall back to coordinates if no address is configured.
        self.addline1 = self.config.get(CONF_ADDRESS_LINE1, "")
        self.addline2 = self.config.get(CONF_ADDRESS_LINE2, "")
        self.addcity = self.config.get(CONF_CITY, "")
        self.addstate = self.config.get(CONF_STATE, "")
        self.addzip = self.config.get(CONF_ZIP, "")

    @property
    def latitude(self):
        """Return latitude from integration config or Home Assistant config."""
        return self.config.get(CONF_LATITUDE, self.hass.config.latitude)

    @property
    def longitude(self):
        """Return longitude from integration config or Home Assistant config."""
        return self.config.get(CONF_LONGITUDE, self.hass.config.longitude)

    @property
    def access_token(self):
        """Return the currently stored Noonlight access token."""
        return self._access_token_response.get("token")

    @property
    def access_token_expiry(self):
        """Return the timestamp when the current access token expires."""
        return self._access_token_response.get("expires", dt_util.utc_from_timestamp(0))

    @property
    def access_token_expires_in(self):
        """Return the remaining lifetime of the current access token."""
        return self.access_token_expiry - dt_util.utcnow()

    @property
    def should_token_be_renewed(self):
        """Return true when there is no token or it is close to expiring."""
        return (
            self.access_token is None
            or self.access_token_expires_in <= self._time_to_renew
        )

    async def check_api_token(self, force_renew=False, token_endpoint_override=None):
        """Check whether the Noonlight API token needs renewal and renew it.

        Args:
            force_renew: Force a token renewal even if the current token has
                sufficient lifetime remaining. Dispatch calls use this to avoid
                sending an alarm with stale or environment-mismatched credentials.
            token_endpoint_override: Optional token endpoint to use for this
                renewal. This is how service calls can choose production vs
                sandbox token behavior at runtime.

        Returns:
            True when a valid token is available, otherwise False.
        """
        _LOGGER.debug(
            "Checking if token needs renewal, expires: {0:.1f}h".format(
                self.access_token_expires_in.total_seconds() / 3600.0
            )
        )

        if self.should_token_be_renewed or force_renew:
            try:
                _LOGGER.debug("Renewing Noonlight access token")
                path = token_endpoint_override or self.config.get(CONF_TOKEN_ENDPOINT)

                if token_endpoint_override:
                    # Log at warning level because endpoint overrides are powerful
                    # and intentional. This makes routing mistakes visible in logs.
                    _LOGGER.warning(
                        "Using overridden Noonlight token endpoint: %s",
                        token_endpoint_override,
                    )

                data = {
                    "id": self.config.get(CONF_ID),
                    "secret": self.config.get(CONF_SECRET),
                }
                headers = {"Content-Type": "application/json"}

                async with self._websession.post(
                    path, json=data, headers=headers
                ) as resp:
                    token_response = await resp.json()

                if "token" in token_response and "expires" in token_response:
                    self._set_token_response(token_response)
                    _LOGGER.debug("Token renewed successfully")
                    async_dispatcher_send(self.hass, EVENT_NOONLIGHT_TOKEN_REFRESHED)
                    return True

                raise NoonlightException(
                    "unexpected token_response: {}".format(token_response)
                )

            except Exception:
                _LOGGER.exception("Failed to renew Noonlight token")
                return False

        return True

    def _set_token_response(self, token_response):
        """Normalize, store, and apply a token endpoint response."""
        expires = dt_util.parse_datetime(token_response["expires"])
        if expires is not None:
            token_response["expires"] = expires
        else:
            # Failing closed is safer than pretending an invalid expiry is valid.
            token_response["expires"] = dt_util.utc_from_timestamp(0)

        self.client.set_token(token=token_response.get("token"))
        self._access_token_response = token_response

    async def update_alarm_status(self):
        """Return the status of the last alarm object, if one exists."""
        if self._alarm is not None:
            return await self._alarm.get_status()

    def _fire_noonlight_event(self, event_type, event_data):
        """Fire a Home Assistant event for Noonlight dispatch observability.

        These events are used by Home Assistant automations for logging,
        dashboards, and fallback escalation when dispatch fails.
        """
        self.hass.bus.async_fire(event_type, event_data)

    async def create_alarm(
        self,
        alarm_types=[nl.NOONLIGHT_SERVICES_POLICE],
        alarm_cause=None,
        instructions=None,
        api_endpoint_override=None,
        token_endpoint_override=None,
        server_token_override=None,
    ):
        """Create a Noonlight alarm.

        This method supports both the original integration behavior and the
        dispatch-specific flow used by this fork.

        Runtime override behavior:
        - api_endpoint_override chooses the API base URL for this dispatch.
        - token_endpoint_override chooses the token renewal endpoint.
        - server_token_override supplies a sandbox server token for sandbox
          dispatch testing.

        Safety behavior:
        - Sandbox dispatch requires a sandbox server token.
        - Production dispatch rejects sandbox server token overrides.
        - Token renewal failure fires a Home Assistant failure event and stops
          the dispatch attempt.
        - Any API exception fires a Home Assistant failure event.
        """
        services = {}
        for alarm_type in alarm_types or ():
            if alarm_type in CONST_NOONLIGHT_SERVICE_TYPES:
                services[alarm_type] = True

        # Resolve runtime endpoints. Overrides are used by the service caller,
        # usually a Home Assistant script, to switch between sandbox and
        # production without changing the saved integration configuration.
        api_endpoint = (api_endpoint_override or self.config.get(CONF_API_ENDPOINT, "")).strip()
        token_endpoint = (token_endpoint_override or self.config.get(CONF_TOKEN_ENDPOINT, "")).strip()
        clean_server_token_override = (
            server_token_override.strip()
            if isinstance(server_token_override, str)
            else ""
        )

        # Environment detection is intentionally endpoint-based so it follows
        # the actual URL being used for this dispatch attempt.
        is_sandbox = "api-sandbox.noonlight.com" in api_endpoint
        is_production = "api.noonlight.com" in api_endpoint and not is_sandbox

        event_base = {
            "api_endpoint": api_endpoint,
            "environment": "sandbox" if is_sandbox else "production" if is_production else "unknown",
            "alarm_cause": alarm_cause,
            "services": list(services.keys()),
        }

        self._fire_noonlight_event(EVENT_NOONLIGHT_ALARM_ATTEMPTED, event_base)

        if not services:
            msg = "No valid Noonlight service type was supplied."
            _LOGGER.error(msg)
            self._fire_noonlight_event(
                EVENT_NOONLIGHT_ALARM_FAILED,
                {**event_base, "error": msg},
            )
            return False

        if is_sandbox and not clean_server_token_override:
            msg = (
                "Noonlight sandbox endpoint was selected, but no sandbox server token "
                "was supplied. Failing closed and not calling production."
            )
            _LOGGER.error(msg)
            self._fire_noonlight_event(
                EVENT_NOONLIGHT_ALARM_FAILED,
                {**event_base, "error": msg},
            )
            return False

        if is_production and clean_server_token_override:
            msg = (
                "Noonlight production endpoint was selected, but a sandbox server token "
                "override was also supplied. Failing closed and not dispatching."
            )
            _LOGGER.error(msg)
            self._fire_noonlight_event(
                EVENT_NOONLIGHT_ALARM_FAILED,
                {**event_base, "error": msg},
            )
            return False

        if api_endpoint_override:
            _LOGGER.warning(
                "Using overridden Noonlight API endpoint: %s",
                api_endpoint,
            )

        self.client.set_base_url(api_endpoint)

        if clean_server_token_override:
            # Sandbox dispatch can use a provided server token directly. This is
            # intentionally separate from production token renewal.
            _LOGGER.warning("Using overridden Noonlight server token")
            self.client.set_token(token=clean_server_token_override)
        else:
            # Production and non-server-token flows must renew through the
            # configured or overridden token endpoint before dispatch.
            token_ok = await self.check_api_token(
                force_renew=True,
                token_endpoint_override=token_endpoint,
            )
            if not token_ok:
                msg = "Noonlight token renewal failed. Alarm was not dispatched."
                _LOGGER.error(msg)
                self._fire_noonlight_event(
                    EVENT_NOONLIGHT_ALARM_FAILED,
                    {**event_base, "error": msg},
                )
                return False

        try:
            # Optional developer token compatibility. This preserves the existing
            # behavior while allowing sandbox server-token dispatch to bypass it.
            if self.config.get(CONF_DEV_TOKEN) and not clean_server_token_override:
                self.client.set_token(token=self.config.get(CONF_DEV_TOKEN))

            if "dispatch" in api_endpoint:
                # Dispatch endpoint payload. This includes address, contact,
                # PIN, service selection, and optional operator instructions.
                alarm_body = {
                    "location": {
                        "address": {
                            "line1": self.addline1,
                            "line2": self.addline2 or "N/A",
                            "city": self.addcity,
                            "state": self.addstate,
                            "zip": self.addzip,
                        }
                    },
                    "name": self.config.get(CONF_NAME),
                    "phone": self.config.get(CONF_PHONE),
                    "pin": self.config.get(CONF_PIN),
                }

                dispatch_instructions = instructions or self.config.get(CONF_INSTRUCTIONS)

                # Put the trigger cause at the front of the instructions so a
                # Noonlight operator can see the important sensor context first.
                if alarm_cause:
                    if dispatch_instructions:
                        dispatch_instructions = (
                            f"Alarm cause is {alarm_cause}. {dispatch_instructions}"
                        )
                    else:
                        dispatch_instructions = f"Alarm cause is {alarm_cause}."

                if dispatch_instructions:
                    alarm_body["instructions"] = {"entry": dispatch_instructions}

                if services:
                    alarm_body["services"] = services

                _LOGGER.warning("Noonlight alarm body: %s", alarm_body)

                self._alarm = await self.client.create_alarm(body=alarm_body)

                # Optional second contact. Some dispatch flows support adding a
                # secondary person after the alarm is created.
                if self.config.get(CONF_NAME2) and self.config.get(CONF_PHONE2):
                    await self.client._post(
                        f"{self.client.alarms_url}/{self._alarm.id}/people",
                        data=[
                            {
                                "name": self.config.get(CONF_NAME2),
                                "phone": self.config.get(CONF_PHONE2),
                                "pin": self.config.get(CONF_PIN),
                            }
                        ],
                    )
            else:
                # Original/non-dispatch style payload. If an address is
                # configured, use it. Otherwise fall back to Home Assistant
                # coordinates or configured coordinates.
                if len(self.addline1) > 0:
                    alarm_body = {
                        "location.address": {
                            "line1": self.addline1,
                            "city": self.addcity,
                            "state": self.addstate,
                            "zip": self.addzip,
                        }
                    }
                    if len(self.addline2) > 0:
                        alarm_body["location.address"]["line2"] = self.addline2
                else:
                    alarm_body = {
                        "location.coordinates": {
                            "lat": self.latitude,
                            "lng": self.longitude,
                            "accuracy": 5,
                        }
                    }

                if services:
                    alarm_body["services"] = services

                _LOGGER.warning("Noonlight alarm body: %s", alarm_body)

                self._alarm = await self.client.create_alarm(body=alarm_body)

        except Exception as err:
            msg = f"Failed to send alarm to Noonlight: {type(err).__name__}: {err}"
            _LOGGER.exception("Failed to send alarm to Noonlight")
            self._fire_noonlight_event(
                EVENT_NOONLIGHT_ALARM_FAILED,
                {**event_base, "error": msg},
            )
            return False

        if self._alarm and self._alarm.status == CONST_ALARM_STATUS_ACTIVE:
            event_data = {
                **event_base,
                "alarm_id": getattr(self._alarm, "id", None),
                "status": getattr(self._alarm, "status", None),
            }
            async_dispatcher_send(self.hass, EVENT_NOONLIGHT_ALARM_CREATED)
            self._fire_noonlight_event(EVENT_NOONLIGHT_ALARM_CREATED, event_data)

            _LOGGER.info(
                "Noonlight alarm initiated. id: %s status: %s environment: %s",
                self._alarm.id,
                self._alarm.status,
                event_base["environment"],
            )

            return True

        msg = "Noonlight alarm call completed, but no active alarm object was returned."
        _LOGGER.error(msg)
        self._fire_noonlight_event(
            EVENT_NOONLIGHT_ALARM_FAILED,
            {**event_base, "error": msg},
        )
        return False
