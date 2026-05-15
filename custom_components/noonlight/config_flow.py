import logging
from typing import TYPE_CHECKING, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_ID, CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME, CONF_PIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .const import (
    CONF_ADDRESS_LINE1,
    CONF_ADDRESS_LINE2,
    CONF_API_ENDPOINT,
    CONF_CITY,
    CONF_INSTRUCTIONS,
    CONF_LOCATION_MODE,
    CONF_NAME2,
    CONF_PHONE,
    CONF_PHONE2,
    CONF_SECRET,
    CONF_STATE,
    CONF_TOKEN_ENDPOINT,
    CONF_ZIP,
    DEFAULT_API_ENDPOINT,
    DEFAULT_NAME,
    DEFAULT_TOKEN_ENDPOINT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# These are the two supported location entry modes.
#
# The selected value is stored in the config entry data under CONF_LOCATION_MODE.
# Later steps use that stored value to decide whether to ask the user for
# latitude/longitude coordinates or a full street address.
#
LOCATION_MODE_LIST = [
    selector.SelectOptionDict(label="Use Latitude/Longitude", value="latlong"),
    selector.SelectOptionDict(label="Use Address", value="address"),
]

# USPS-style state abbreviations used by the address location screen.
#
# This is intentionally kept as a simple static list because the config flow only
# needs to collect the value and pass it through to the integration config entry.
#
STATES = [
    "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI",
    "IA", "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN",
    "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA",
    "WI", "WV", "WY",
]


async def _async_build_noonlight_schema(
    hass: HomeAssistant, user_input: dict | None, default_dict: dict
) -> Any:
    """Build the setup screen for name and location mode."""

    # Home Assistant calls schema builders both before and after user input.
    # Normalizing None to an empty dict lets the helper below always read from
    # user_input safely without adding repeated None checks.
    if user_input is None:
        user_input = {}

    # Values shown in the form should prefer what the user just typed, then fall
    # back to existing config entry data or caller-provided defaults.
    #
    # Returning an empty string for None avoids Home Assistant selector problems
    # where a text selector receives None instead of a string-like value.
    def _get_default(key: str, fallback_default: Any = None) -> Any:
        value = user_input.get(key, default_dict.get(key, fallback_default))
        return "" if value is None else value

    # This first screen intentionally stays small.
    #
    # It only collects the display name and the location mode. The detailed
    # location fields are collected on the following step so the user only sees
    # the fields relevant to the selected location mode.
    return vol.Schema(
        {
            vol.Required(
                CONF_NAME,
                default=_get_default(CONF_NAME, DEFAULT_NAME),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Required(
                CONF_LOCATION_MODE,
                default=_get_default(CONF_LOCATION_MODE, "latlong"),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=LOCATION_MODE_LIST,
                    multiple=False,
                    custom_value=False,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        }
    )


async def _async_build_v2_dispatch_schema(
    hass: HomeAssistant, user_input: dict | None, default_dict: dict
) -> Any:
    """Build the dispatch metadata screen.

    Credentials, endpoints, contacts, and instructions are optional here so the
    integration can be installed first and completed later. Dispatch-time checks
    should prevent real calls when required production credentials are missing.
    """

    # Normalize input for the same reason as the earlier schema builder.
    # The config flow may be rendering the form for the first time, in which case
    # user_input will be None.
    if user_input is None:
        user_input = {}

    # This screen is mostly text fields. Convert saved values to strings before
    # handing them to Home Assistant selectors.
    #
    # This avoids the "expected str" class of issue when a saved value is None,
    # numeric, or otherwise not already a string.
    def _get_text_default(key: str, fallback_default: Any = "") -> str:
        value = user_input.get(key, default_dict.get(key, fallback_default))
        if value is None:
            return ""
        return str(value)

    # This schema intentionally keeps every dispatch metadata field optional.
    #
    # That preserves the current behavior: the integration can be configured
    # before all credentials or contact details are entered. The runtime dispatch
    # path should be responsible for validating whether a real alarm call is safe.
    return vol.Schema(
        {
            vol.Optional(
                CONF_ID,
                default=_get_text_default(CONF_ID),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional(
                CONF_SECRET,
                default=_get_text_default(CONF_SECRET),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional(
                CONF_API_ENDPOINT,
                default=_get_text_default(CONF_API_ENDPOINT, DEFAULT_API_ENDPOINT),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional(
                CONF_TOKEN_ENDPOINT,
                default=_get_text_default(CONF_TOKEN_ENDPOINT, DEFAULT_TOKEN_ENDPOINT),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional(
                CONF_PHONE,
                default=_get_text_default(CONF_PHONE),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional(
                CONF_PIN,
                default=_get_text_default(CONF_PIN),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional(
                CONF_NAME2,
                default=_get_text_default(CONF_NAME2),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional(
                CONF_PHONE2,
                default=_get_text_default(CONF_PHONE2),
            ): selector.TextSelector(selector.TextSelectorConfig()),
            vol.Optional(
                CONF_INSTRUCTIONS,
                default=_get_text_default(CONF_INSTRUCTIONS),
            ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
        }
    )


async def _async_build_latlong_schema(
    hass: HomeAssistant, user_input: dict | None, default_dict: dict
) -> Any:
    """Build the latitude/longitude location screen."""

    # Normalize user_input so the default helper can read it safely.
    if user_input is None:
        user_input = {}

    # Latitude and longitude may come from user input, existing config entry data,
    # or Home Assistant's configured latitude/longitude defaults.
    def _get_default(key: str, fallback_default: Any = None) -> Any:
        return user_input.get(key, default_dict.get(key, fallback_default))

    # Home Assistant's built-in latitude and longitude validators are retained.
    #
    # These validators preserve the current behavior and avoid introducing a new
    # validation path in this cleanup-only pass.
    return vol.Schema(
        {
            vol.Optional(
                CONF_LATITUDE,
                default=_get_default(CONF_LATITUDE),
            ): cv.latitude,
            vol.Optional(
                CONF_LONGITUDE,
                default=_get_default(CONF_LONGITUDE),
            ): cv.longitude,
        }
    )


async def _async_build_address_schema(
    hass: HomeAssistant, user_input: dict | None, default_dict: dict
) -> Any:
    """Build the address location screen."""

    # Normalize user_input so the default helper can read it safely.
    if user_input is None:
        user_input = {}

    # Address field defaults come from the most recent user input first, then the
    # current config entry data. This keeps reconfigure screens pre-filled.
    def _get_default(key: str, fallback_default: Any = None) -> Any:
        return user_input.get(key, default_dict.get(key, fallback_default))

    build_schema = vol.Schema({})

    # Address line 1 is required.
    #
    # If no existing value is available, show the required field without a
    # default. If a value exists, pre-fill it while keeping the field required.
    #
    if _get_default(CONF_ADDRESS_LINE1) is None:
        build_schema = build_schema.extend(
            {vol.Required(CONF_ADDRESS_LINE1): selector.TextSelector(selector.TextSelectorConfig())}
        )
    else:
        build_schema = build_schema.extend(
            {
                vol.Required(
                    CONF_ADDRESS_LINE1,
                    default=_get_default(CONF_ADDRESS_LINE1),
                ): selector.TextSelector(selector.TextSelectorConfig())
            }
        )

    # Address line 2 is optional.
    #
    # This is useful for apartment, suite, unit, or other secondary address
    # information. It stays optional whether or not a prior value exists.
    #
    if _get_default(CONF_ADDRESS_LINE2) is None:
        build_schema = build_schema.extend(
            {vol.Optional(CONF_ADDRESS_LINE2): selector.TextSelector(selector.TextSelectorConfig())}
        )
    else:
        build_schema = build_schema.extend(
            {
                vol.Optional(
                    CONF_ADDRESS_LINE2,
                    default=_get_default(CONF_ADDRESS_LINE2),
                ): selector.TextSelector(selector.TextSelectorConfig())
            }
        )

    # City is required.
    #
    # If this is a new config flow there is no default. During reconfiguration,
    # the existing city is shown as the default.
    #
    if _get_default(CONF_CITY) is None:
        build_schema = build_schema.extend(
            {vol.Required(CONF_CITY): selector.TextSelector(selector.TextSelectorConfig())}
        )
    else:
        build_schema = build_schema.extend(
            {
                vol.Required(
                    CONF_CITY,
                    default=_get_default(CONF_CITY),
                ): selector.TextSelector(selector.TextSelectorConfig())
            }
        )

    # State is selected from the static STATES list above.
    #
    # The existing behavior is preserved here, including the required/optional
    # distinction based on whether a previous value is already present.
    #
    if _get_default(CONF_STATE) is None:
        build_schema = build_schema.extend(
            {
                vol.Required(CONF_STATE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=STATES,
                        multiple=False,
                        custom_value=False,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
    else:
        build_schema = build_schema.extend(
            {
                vol.Optional(
                    CONF_STATE,
                    default=_get_default(CONF_STATE),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=STATES,
                        multiple=False,
                        custom_value=False,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    # ZIP code is required.
    #
    # It is collected as text because ZIP codes may contain leading zeroes and
    # should not be treated as numeric values.
    #
    if _get_default(CONF_ZIP) is None:
        build_schema = build_schema.extend(
            {vol.Required(CONF_ZIP): selector.TextSelector(selector.TextSelectorConfig())}
        )
    else:
        build_schema = build_schema.extend(
            {
                vol.Required(
                    CONF_ZIP,
                    default=_get_default(CONF_ZIP),
                ): selector.TextSelector(selector.TextSelectorConfig())
            }
        )

    return build_schema


class NoonlightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Noonlight config flow."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow state."""

        # _data accumulates values across multiple config flow screens.
        #
        # Home Assistant config flows are step-based, so each screen contributes
        # part of the final config entry data.
        #
        self._data = {}

        # _errors is passed back to async_show_form.
        #
        # It remains available for future validation errors without changing the
        # current behavior of these screens.
        #
        self._errors = {}

        # _entry is populated during reconfiguration so the final step can update
        # and reload the existing config entry.
        #
        self._entry = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None, yaml_import=False
    ) -> ConfigFlowResult:
        """Handle the first setup step."""

        # Reset form errors every time this step is entered.
        self._errors = {}

        if user_input is not None:
            # Store the user's first-screen selections.
            #
            # This includes the integration display name and the selected
            # location mode.
            #
            self._data.update(user_input)

            # YAML import is a special path that should create the config entry
            # immediately instead of walking through all interactive screens.
            #
            if yaml_import:
                self._data.update(
                    {
                        CONF_NAME: self._data.get(CONF_NAME, DEFAULT_NAME),
                        CONF_LOCATION_MODE: self._data.get(CONF_LOCATION_MODE, "latlong"),
                        CONF_LATITUDE: self._data.get(CONF_LATITUDE, self.hass.config.latitude),
                        CONF_LONGITUDE: self._data.get(CONF_LONGITUDE, self.hass.config.longitude),
                    }
                )

                # Keep debug logging useful without dumping credentials, tokens,
                # endpoint overrides, phone numbers, or instructions into logs.
                _LOGGER.debug("Creating Noonlight entry from YAML import")

                return self.async_create_entry(
                    title=self._data[CONF_NAME], data=self._data
                )

            # Continue to the correct location detail screen based on the user's
            # selected location mode.
            _LOGGER.debug("Processing Noonlight setup location mode")
            if self._data.get(CONF_LOCATION_MODE) == "latlong":
                return await self.async_step_latlong()
            return await self.async_step_address()

        # Defaults used when the first setup form is displayed for a new entry.
        defaults = {
            CONF_NAME: DEFAULT_NAME,
            CONF_API_ENDPOINT: DEFAULT_API_ENDPOINT,
            CONF_TOKEN_ENDPOINT: DEFAULT_TOKEN_ENDPOINT,
        }

        # Show the first setup form.
        #
        # This step only asks for name and location mode. The actual location
        # details are collected by the next step.
        #
        return self.async_show_form(
            step_id="user",
            data_schema=await _async_build_noonlight_schema(
                self.hass, user_input, defaults
            ),
            errors=self._errors,
        )

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the address setup step."""

        # Reset form errors every time this step is entered.
        self._errors = {}

        if user_input is not None:
            # Store the address fields and then continue to the dispatch metadata
            # screen.
            self._data.update(user_input)
            _LOGGER.debug("Processing Noonlight address setup step")
            return await self.async_step_v2_dispatch()

        # Show the address form for a new setup flow.
        #
        # No existing defaults are supplied here because this is the initial
        # setup path, not the reconfiguration path.
        #
        return self.async_show_form(
            step_id="address",
            data_schema=await _async_build_address_schema(self.hass, user_input, {}),
            errors=self._errors,
        )

    async def async_step_latlong(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the latitude/longitude setup step."""

        # Reset form errors every time this step is entered.
        self._errors = {}

        if user_input is not None:
            # Store the coordinate fields and then continue to the dispatch
            # metadata screen.
            self._data.update(user_input)
            _LOGGER.debug("Processing Noonlight latitude/longitude setup step")
            return await self.async_step_v2_dispatch()

        # Use Home Assistant's configured location as the default for a new setup
        # flow. This keeps the setup experience simple when HA already knows the
        # installation location.
        defaults = {
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
        }

        # Show the latitude/longitude form.
        return self.async_show_form(
            step_id="latlong",
            data_schema=await _async_build_latlong_schema(
                self.hass, user_input, defaults
            ),
            errors=self._errors,
        )

    async def async_step_v2_dispatch(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the dispatch metadata setup step."""

        # Reset form errors every time this step is entered.
        self._errors = {}

        if user_input is not None:
            # Store optional dispatch metadata and create the config entry.
            #
            # This is the final interactive setup step for a new config entry.
            #
            self._data.update(user_input)
            _LOGGER.debug("Creating Noonlight entry after dispatch metadata step")
            return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

        # Show the dispatch metadata form.
        #
        # Existing accumulated setup data is passed as defaults so any values
        # already present in _data can pre-fill this screen.
        #
        return self.async_show_form(
            step_id="v2_dispatch",
            data_schema=await _async_build_v2_dispatch_schema(
                self.hass, user_input, self._data
            ),
            errors=self._errors,
        )

    async def async_step_import(
        self, import_config: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Import a config entry from configuration.yaml."""

        # Validate the minimum required YAML fields before attempting to import.
        #
        # This preserves the current behavior: YAML imports are rejected if these
        # required fields are missing.
        #
        if (
            import_config.get(CONF_ID, None) is None
            or import_config.get(CONF_SECRET, None) is None
            or import_config.get(CONF_API_ENDPOINT, None) is None
            or import_config.get(CONF_TOKEN_ENDPOINT, None) is None
        ):
            # Do not log the full YAML config because it may contain credentials,
            # endpoint overrides, phone numbers, or instructions.
            _LOGGER.error("Invalid Noonlight YAML config. Cannot import.")
            return

        # Reuse the normal user setup path with yaml_import=True so the config
        # entry is created without showing the interactive forms.
        _LOGGER.debug("Importing Noonlight YAML config")
        return await self.async_step_user(user_input=import_config, yaml_import=True)

    async def async_step_reconfigure(
        self, _: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start a user-initiated reconfiguration flow."""

        # Home Assistant provides the config entry id in the flow context when a
        # reconfiguration flow is started from an existing integration entry.
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        # TYPE_CHECKING keeps static type checkers happy while avoiding a runtime
        # behavior change. Home Assistant should provide the entry here.
        if TYPE_CHECKING:
            assert entry is not None

        # Copy the existing config entry data into working flow state.
        #
        # The following reconfigure screens mutate _data and finally save it back
        # to the same config entry.
        #
        self._data = dict(entry.data)
        self._entry = entry

        # Start reconfiguration with the same first screen as setup: name and
        # location mode.
        return await self.async_step_reconfigure_confirm()

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the first reconfiguration step."""

        # Reset form errors every time this step is entered.
        self._errors = {}

        if user_input is not None:
            # Store updated name and location mode before choosing the next
            # reconfiguration screen.
            self._data.update(user_input)
            _LOGGER.debug("Processing Noonlight reconfiguration location mode")

            # Route to the correct location reconfiguration step.
            if self._data.get(CONF_LOCATION_MODE) == "latlong":
                return await self.async_step_reconfig_latlong()
            return await self.async_step_reconfig_address()

        # Show the first reconfiguration form, pre-filled from the current config
        # entry data.
        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=await _async_build_noonlight_schema(
                self.hass, user_input, self._data
            ),
            errors=self._errors,
        )

    async def async_step_reconfig_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the address reconfiguration step."""

        # Reset form errors every time this step is entered.
        self._errors = {}

        if user_input is not None:
            # Store the updated address fields.
            self._data.update(user_input)

            # Remove latitude/longitude fields when the user switches to address
            # mode. This keeps the saved config entry data aligned with the
            # selected location mode.
            self._data.pop(CONF_LATITUDE, None)
            self._data.pop(CONF_LONGITUDE, None)

            # If address line 2 was left blank or omitted, remove it from stored
            # data rather than keeping a stale prior value.
            if user_input.get(CONF_ADDRESS_LINE2, None) is None:
                self._data.pop(CONF_ADDRESS_LINE2, None)

            # Continue to the dispatch metadata reconfiguration screen.
            _LOGGER.debug("Processing Noonlight address reconfiguration step")
            return await self.async_step_reconfig_v2_dispatch()

        # Show the address reconfiguration form, pre-filled from the current
        # config entry data.
        return self.async_show_form(
            step_id="reconfig_address",
            data_schema=await _async_build_address_schema(
                self.hass, user_input, self._data
            ),
            errors=self._errors,
        )

    async def async_step_reconfig_latlong(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the latitude/longitude reconfiguration step."""

        # Reset form errors every time this step is entered.
        self._errors = {}

        if user_input is not None:
            # Store the updated coordinate fields.
            self._data.update(user_input)

            # Remove address fields when the user switches to latitude/longitude
            # mode. This keeps the saved config entry data aligned with the
            # selected location mode.
            self._data.pop(CONF_ADDRESS_LINE1, None)
            self._data.pop(CONF_ADDRESS_LINE2, None)
            self._data.pop(CONF_CITY, None)
            self._data.pop(CONF_STATE, None)
            self._data.pop(CONF_ZIP, None)

            # Continue to the dispatch metadata reconfiguration screen.
            _LOGGER.debug("Processing Noonlight latitude/longitude reconfiguration step")
            return await self.async_step_reconfig_v2_dispatch()

        # Show the latitude/longitude reconfiguration form, pre-filled from the
        # current config entry data.
        return self.async_show_form(
            step_id="reconfig_latlong",
            data_schema=await _async_build_latlong_schema(
                self.hass, user_input, self._data
            ),
            errors=self._errors,
        )

    async def async_step_reconfig_v2_dispatch(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle dispatch metadata during reconfiguration."""

        # Reset form errors every time this step is entered.
        self._errors = {}

        if user_input is not None:
            # Store updated optional dispatch metadata.
            self._data.update(user_input)

            # Save the updated config entry data.
            #
            # The existing entry is updated in place rather than creating a new
            # entry, which is the expected Home Assistant reconfiguration flow.
            #
            _LOGGER.debug("Saving Noonlight reconfiguration changes")
            self.hass.config_entries.async_update_entry(self._entry, data=self._data)

            # Reload the integration so runtime code picks up the updated config
            # entry data immediately.
            #
            await self.hass.config_entries.async_reload(self._entry.entry_id)

            # Finish the reconfiguration flow with Home Assistant's standard
            # success abort reason.
            #
            return self.async_abort(reason="reconfigure_successful")

        # Show the dispatch metadata reconfiguration form, pre-filled from the
        # current config entry data.
        #
        return self.async_show_form(
            step_id="reconfig_v2_dispatch",
            data_schema=await _async_build_v2_dispatch_schema(
                self.hass, user_input, self._data
            ),
            errors=self._errors,
        )