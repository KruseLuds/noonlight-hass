# Changelog

## v1.1.0

### Added

* `noonlight.cancel_alarm` service for explicitly cancelling a known alarm with a nonblank PIN.
* Route persistence for up to 24 hours so cancellation stays in the environment where the alarm was created. No access tokens are stored in Home Assistant's persistent route store.
* `noonlight_alarm_canceled` success event and `noonlight_alarm_failed` events marked `action: cancel`.
* Automated cancellation regression tests and a GitHub Actions `pytest` workflow.
* Contact-phone format validation, including rejection of non-ASCII numeral characters.

### Safety and reliability

* Reject unknown, expired, and missing alarm IDs without contacting Noonlight.
* Prevent sandbox and production credentials or routes from being silently interchanged.
* Reject cancellation attempts with blank or missing PINs.
* Reuse valid tokens when available and refresh broker tokens before expiry, with a bounded 401 retry and request timeouts.
* Record the alarm's cancellation route before adding an optional secondary contact, so a secondary-contact error does not misreport a successfully created primary alarm.
* Avoid logging alarm request bodies containing personal contact details or PINs.

### Notes

* Alarmo or another alarm panel being disarmed does not cancel a Noonlight dispatch. Cancellation requires an explicit action, and the integration reports success only on a confirmed API response.
* A failed cancellation does not establish that an active dispatch has stopped. Confirm directly with Noonlight if needed.
* Testing on the sandbox is not equivalent to verification of the production authentication path. Coordinate any live dispatch tests appropriately.
* No automatic migrations or Home Assistant entity renames are required by these changes.

### Contributors

* [ChuckBuilds](https://github.com/ChuckBuilds) contributed the cancellation functionality and automated test suite through [PR #2](https://github.com/KruseLuds/noonlight-hass/pull/2). Additional safety hardening and release preparation were completed by the repository maintainer.

## v1.0.1 (2026-08-20)

* Fixed per-action endpoint overrides for `noonlight.create_alarm`, including sandbox endpoints with `server_token_override`.

## v1.0.0 (2026-08-05)

* Initial stable release of Noonlight Enhanced, including Dispatch API v2 support and richer alarm context.
