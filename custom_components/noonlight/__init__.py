"""Noonlight integration for Home Assistant."""

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
from homeassistant.helpers.event import async_track_point_in_utc_time
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
TOKEN_CHECK_INTERVAL = timedelta(minutes=15)

EVENT_NOONLIGHT_ALARM_ATTEMPTED = "noonlight_alarm_attempted"
EVENT_NOONLIGHT_ALARM_FAILED = "noonlight_alarm_failed"
EVENT_NOONLIGHT_WEBHOOK_RECEIVED = "noonlight_webhook_received"

WEBHOOK_ID = "noonlight_dispatch_events"


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
                vol.Optional(CONF_DEV_TOKEN): cv.string,
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
    """Set up from YAML."""
    if DOMAIN not in config:
        return True

    _LOGGER.debug("[async_setup] config: %s", config[DOMAIN])
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

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data=config[DOMAIN],
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""

    _LOGGER.debug("[init async_setup_entry] entry: %s", entry.data)
    noonlight_integration = NoonlightIntegration(hass, entry.data)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = noonlight_integration

    async def handle_create_alarm_service(call):
        """Create a Noonlight alarm from a Home Assistant service call."""
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
        """Receive Noonlight webhook events."""
        try:
            payload = await request.json()
        except Exception:
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

    async def check_api_token(now):
        """Check if the current API token has expired and renew if so."""
        next_check_interval = TOKEN_CHECK_INTERVAL

        result = await noonlight_integration.check_api_token()

        if not result:
            _LOGGER.error("API token failed renewal, retrying in 3 min")
            check_api_token.fail_count += 1
            next_check_interval = timedelta(minutes=3)
        else:
            if check_api_token.fail_count > 0:
                _LOGGER.info("Noonlight API token renewed successfully after failure.")
            check_api_token.fail_count = 0

        async_track_point_in_utc_time(
            hass, check_api_token, dt_util.utcnow() + next_check_interval
        )

    check_api_token.fail_count = 0
    async_track_point_in_utc_time(hass, check_api_token, dt_util.utcnow())

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading: %s", entry.data)

    webhook.async_unregister(hass, WEBHOOK_ID)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)

    return unload_ok


class NoonlightException(HomeAssistantError):
    """General exception for Noonlight Integration."""

    pass


class NoonlightIntegration:
    """Integration for interacting with Noonlight from Home Assistant."""

    def __init__(self, hass, conf):
        """Initialize NoonlightIntegration."""
        self.hass = hass
        self.config = conf
        self._access_token_response = {}
        self._alarm = None
        self._time_to_renew = timedelta(hours=2)
        self._websession = async_get_clientsession(self.hass)
        self.client = nl.NoonlightClient(
            token=self.access_token, session=self._websession
        )
        self.client.set_base_url(self.config[CONF_API_ENDPOINT])

        self.addline1 = self.config.get(CONF_ADDRESS_LINE1, "")
        self.addline2 = self.config.get(CONF_ADDRESS_LINE2, "")
        self.addcity = self.config.get(CONF_CITY, "")
        self.addstate = self.config.get(CONF_STATE, "")
        self.addzip = self.config.get(CONF_ZIP, "")

    @property
    def latitude(self):
        """Return latitude from the Home Assistant configuration."""
        return self.config.get(CONF_LATITUDE, self.hass.config.latitude)

    @property
    def longitude(self):
        """Return longitude from the Home Assistant configuration."""
        return self.config.get(CONF_LONGITUDE, self.hass.config.longitude)

    @property
    def access_token(self):
        """Return the access token from the Noonlight Configuration."""
        return self._access_token_response.get("token")

    @property
    def access_token_expiry(self):
        """Return the timestamp when the access token expires."""
        return self._access_token_response.get("expires", dt_util.utc_from_timestamp(0))

    @property
    def access_token_expires_in(self):
        """Return the timedelta until the token expires."""
        return self.access_token_expiry - dt_util.utcnow()

    @property
    def should_token_be_renewed(self):
        """Return true if the token needs to be renewed."""
        return (
            self.access_token is None
            or self.access_token_expires_in <= self._time_to_renew
        )

    async def check_api_token(self, force_renew=False, token_endpoint_override=None):
        """Check if Noonlight API token needs renewal and renew if so."""
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
        """Store the latest token response."""
        expires = dt_util.parse_datetime(token_response["expires"])
        if expires is not None:
            token_response["expires"] = expires
        else:
            token_response["expires"] = dt_util.utc_from_timestamp(0)

        self.client.set_token(token=token_response.get("token"))
        self._access_token_response = token_response

    async def update_alarm_status(self):
        """Update the status of the current alarm."""
        if self._alarm is not None:
            return await self._alarm.get_status()

    def _fire_noonlight_event(self, event_type, event_data):
        """Fire a Home Assistant event for Noonlight dispatch status."""
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
        """Create a new alarm."""
        services = {}
        for alarm_type in alarm_types or ():
            if alarm_type in CONST_NOONLIGHT_SERVICE_TYPES:
                services[alarm_type] = True

        api_endpoint = (api_endpoint_override or self.config.get(CONF_API_ENDPOINT, "")).strip()
        token_endpoint = (token_endpoint_override or self.config.get(CONF_TOKEN_ENDPOINT, "")).strip()
        clean_server_token_override = (
            server_token_override.strip()
            if isinstance(server_token_override, str)
            else ""
        )

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
            _LOGGER.warning("Using overridden Noonlight server token")
            self.client.set_token(token=clean_server_token_override)
        else:
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
            if self.config.get(CONF_DEV_TOKEN) and not clean_server_token_override:
                self.client.set_token(token=self.config.get(CONF_DEV_TOKEN))

            if "dispatch" in api_endpoint:
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
