"""Expose a lightweight Noonlight Enhanced information entity.

This platform intentionally retains a single switch entity so the Noonlight
Enhanced integration appears cleanly inside Home Assistant's Integrations UI.

Historically, the original Noonlight integration used a switch entity as the
primary mechanism for triggering alarms. Noonlight Enhanced now performs real
alarm dispatching through the `noonlight.create_alarm` Home Assistant
action/service instead.

This entity is informational only.

Turning this switch on does NOT dispatch an alarm. It creates a Home Assistant
persistent notification explaining that dispatches should be created through
the `noonlight.create_alarm` action/service, then immediately turns itself
back off.
"""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DOMAIN,
    EVENT_NOONLIGHT_ALARM_CANCELED,
    EVENT_NOONLIGHT_ALARM_CREATED,
    EVENT_NOONLIGHT_TOKEN_REFRESHED,
    NOONLIGHT_SERVICES_POLICE,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Noonlight Enhanced Info"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities,
) -> None:
    """Create the Noonlight Enhanced information entity from a config entry."""

    _LOGGER.debug(
        "[async_setup_entry] Noonlight integration data loaded for entry_id=%s",
        config_entry.entry_id,
    )

    noonlight_integration = hass.data.get(DOMAIN).get(config_entry.entry_id)
    noonlight_switch = NoonlightSwitch(noonlight_integration)

    async_add_entities([noonlight_switch])

    def noonlight_token_refreshed():
        """Refresh entity state after a token refresh."""
        noonlight_switch.schedule_update_ha_state()

    def noonlight_alarm_canceled():
        """Reflect a canceled alarm in the UI entity state."""
        noonlight_switch._state = False
        noonlight_switch.schedule_update_ha_state()

    def noonlight_alarm_created():
        """Reflect an active alarm in the UI entity state."""
        noonlight_switch._state = True
        noonlight_switch.schedule_update_ha_state()

    async_dispatcher_connect(
        hass,
        EVENT_NOONLIGHT_TOKEN_REFRESHED,
        noonlight_token_refreshed,
    )

    async_dispatcher_connect(
        hass,
        EVENT_NOONLIGHT_ALARM_CANCELED,
        noonlight_alarm_canceled,
    )

    async_dispatcher_connect(
        hass,
        EVENT_NOONLIGHT_ALARM_CREATED,
        noonlight_alarm_created,
    )


class NoonlightSwitch(SwitchEntity):
    """Represent Noonlight Enhanced integration information.

    This entity exists for Home Assistant UI visibility and backward
    compatibility. Real alarm dispatching should be performed through the
    `noonlight.create_alarm` Home Assistant action/service.
    """

    def __init__(self, noonlight_integration):
        """Initialize the Noonlight Enhanced information entity."""

        self.noonlight = noonlight_integration
        self.hass = noonlight_integration.hass

        # Retain the original police service identifier in the unique ID so
        # existing installations do not receive a new duplicate entity.
        self._alarm_type = NOONLIGHT_SERVICES_POLICE

        self._attr_unique_id = (
            f"{self._alarm_type.lower()}_"
            f"{Platform.SWITCH}_"
            f"{self.noonlight.config.get('id', '')}"
        )

        self._attr_name = DEFAULT_NAME
        self._attr_icon = "mdi:information"

        # False is the normal state.
        #
        # The entity is informational only. It briefly accepts a turn-on request
        # only so it can show help text, then immediately resets itself to off.
        self._state = False

    @property
    def available(self):
        """Return whether the information entity is available.

        This entity is informational only and should remain available whenever
        the integration is loaded. Noonlight Enhanced intentionally avoids
        background token polling. Tokens are refreshed on demand during real
        dispatch operations.
        """

        return True

    @property
    def extra_state_attributes(self):
        """Expose integration guidance and current alarm metadata."""

        attr = {
            "primary_dispatch_interface": "noonlight.create_alarm",
            "information_entity_only": True,
            "manual_switch_dispatch_enabled": False,
        }

        if self.noonlight._alarm is not None:
            alarm = self.noonlight._alarm

            attr["alarm_status"] = alarm.status
            attr["alarm_id"] = alarm.id
            attr["alarm_services"] = alarm.services

        return attr

    @property
    def is_on(self):
        """Return the current information entity state."""

        return self._state

    async def async_turn_on(self, **kwargs):
        """Show instructions instead of dispatching an alarm.

        This entity is informational only. Turning it on intentionally does not
        create a Noonlight alarm.
        """

        _LOGGER.warning(
            "Noonlight Enhanced Info switch was turned on manually; "
            "no alarm was dispatched. Use the noonlight.create_alarm action."
        )

        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": "Noonlight Enhanced",
                "message": (
                    "Noonlight Enhanced dispatches alarms through the Home "
                    "Assistant action/service:\n\n"
                    "`noonlight.create_alarm`\n\n"
                    "The visible entity in Devices & Services exists only to "
                    "provide integration visibility, help text, and backward "
                    "compatibility with Home Assistant UI expectations.\n\n"
                    "Automations should call `noonlight.create_alarm` so they "
                    "can include alarm cause, operator instructions, sandbox "
                    "or production routing, and endpoint overrides."
                ),
                "notification_id": "noonlight_enhanced_info",
            },
            blocking=False,
        )

        self._state = False
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Keep the informational entity off."""

        self._state = False
        self.async_write_ha_state()