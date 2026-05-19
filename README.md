# Noonlight Enhanced for Home Assistant

## Overview

Noonlight Enhanced is an unofficial Home Assistant custom integration for the Noonlight Dispatch API.

It is based on the original Noonlight Home Assistant integration and has been extended for modern dispatch workflows, sandbox testing, richer dispatch context, Home Assistant events, webhook handling, improved diagnostics, and advanced automation-driven safety workflows.

As stated in the original integration:

> "Noonlight connects to emergency 9-1-1 services in all 50 U.S. states. Backed by a UL-compliant alarm monitoring center and staffed 24/7 with live operators in the United States, Noonlight is standing by to send help to your home at a moment's notice."

Currently, Noonlight service availability is limited to the United States.

This fork focuses on safer testing, sandbox vs production separation, richer dispatch information, better Home Assistant automation integration, improved observability, advanced routing workflows, and fail-closed safety protections.

## Important Safety Notice

This project is not certified life-safety software.

This integration is provided as-is without warranties of any kind. Using Home Assistant with Noonlight involves multiple independent systems and providers, including Home Assistant, your internet provider, your networking equipment, your cloud or tunnel provider, Noonlight, Konnected token services, cellular/SMS/voice providers, and your own automations and scripts.

Any of these systems may fail.

You are fully responsible for testing your automations, verifying dispatch behavior, validating notifications, confirming address and contact information, maintaining backup safety systems, and understanding the risks of false alarms or failed alarms.

Do not rely solely on this integration for personal safety, fire protection, medical emergencies, or property protection. Always maintain independent safety measures and test regularly.

## Architecture and Design Philosophy

This fork intentionally follows an automation-first, event-driven architecture.

Core design principles:

* Home Assistant remains the orchestration layer
* Noonlight remains the dispatch provider
* The integration remains transport-focused rather than policy-focused
* Notification routing should be externalized to Home Assistant automations
* Testing and production behavior should be explicitly controlled by the user
* Dangerous endpoint combinations should fail closed

### Event-Driven Architecture

Rather than hardcoding notification behavior inside the integration, this fork emits Home Assistant events and allows users to build their own workflows for SMS, voice, dashboards, logging, escalation, and monitoring.

### On-Demand Token Renewal

This fork intentionally does not perform background token polling while idle.

Access tokens are renewed only when an alarm is actually being created.

Benefits:

* no unnecessary token endpoint traffic
* endpoint alignment with the specific runtime dispatch request
* reduced background API noise
* simpler operational behavior

Dispatch model:

Alarm requested
-> resolve runtime endpoints
-> renew token if required
-> create alarm
-> emit Home Assistant events

## What Changed in This Fork

The original integration supported very minimal dispatch context, primarily police, fire, and medical dispatch requests. This fork modernizes and extends the integration so Home Assistant automations can provide much more useful context to Noonlight.

Major additions include:

* Noonlight Dispatch API v2-compatible workflow support
* Sandbox testing support
* Sandbox server token override support
* Production vs sandbox safety protections
* Human-readable alarm cause support
* Dispatch instruction support
* Home Assistant dispatch lifecycle events
* Webhook receiver support
* Improved logging and diagnostics
* API endpoint override support
* Token endpoint override support
* Better Home Assistant automation integration
* Cleaner event-driven architecture

This allows Home Assistant automations to include information such as which sensor triggered, which room or area was involved, whether the alarm is intrusion/fire/medical related, whether the alarm is TEST or LIVE, occupancy context, property access information, dispatcher instructions, and contact workflows.

Examples:

* "Mud room storm door at rear of home opened while system armed Away."
* "Smoke detector activated in basement utility room near furnace."
* "Medical alert button pressed by homeowner."
* "TEST ONLY. DO NOT DISPATCH."

The goal is to provide monitoring operators and first responders with clearer situational awareness at the same time the alarm is created.

## Features

### Core Features

* Home Assistant Noonlight integration
* Police dispatch support
* Fire dispatch support
* Medical dispatch support
* Address-based dispatch support
* Coordinate-based dispatch support
* Home Assistant switch entity support
* Home Assistant service support
* Config Flow UI setup
* Home Assistant event generation
* Improved logging and diagnostics

### Extended Features Added in This Fork

* Noonlight Dispatch API v2-compatible workflow support
* Sandbox testing support
* Sandbox server token override support
* API endpoint override support
* Token endpoint override support
* Human-readable alarm cause support
* Dispatch instruction injection support
* Webhook receiver support
* Dispatch success/failure Home Assistant events
* Fail-closed production/sandbox safety checks
* Improved error handling
* Better Home Assistant automation integration
* Removal of hardcoded notification behavior
* Cleaner event-driven architecture

## Installation

### HACS Installation

1. Open HACS.
2. Go to Integrations.
3. Open the menu in the upper-right corner.
4. Select Custom Repositories.
5. Add this repository URL:

```text
https://github.com/KruseLuds/noonlight-hass
```

6. Category: Integration.
7. Install the integration.
8. Restart Home Assistant.

### Manual Installation

Copy the `custom_components/noonlight` folder into your Home Assistant `custom_components` directory:

```text
/config/custom_components/noonlight
```

Then restart Home Assistant.

## Initial Noonlight Setup

Before configuring the integration, you should create or obtain the Noonlight account and API information needed for your use case.

You will typically need:

* Noonlight Client ID
* Noonlight Client Secret
* A U.S.-based phone number
* Address information or latitude/longitude information
* PIN information
* Home Assistant
* Internet connectivity

Depending on your setup, you may use production Noonlight Dispatch API endpoints, sandbox Noonlight Dispatch API endpoints, or sandbox server token overrides.

The original integration architecture uses Konnected-hosted token broker endpoints to obtain Noonlight access tokens. Advanced users may also use Home Assistant helpers and service-call overrides to switch between sandbox and production workflows.

You can install and configure the integration before all production credentials are finalized. However, you should not attempt LIVE dispatch until credentials, endpoint settings, address information, notification routing, and safety checks have been tested.

## Configuration and Reconfiguration

After installation:

1. Open Home Assistant.
2. Go to Settings -> Devices & Services.
3. Add Integration.
4. Search for Noonlight Enhanced.

The configuration flow is organized to make setup easier:

1. Name and location mode.
2. Address fields or latitude/longitude fields.
3. Credentials, endpoints, contact information, PIN, and instructions.

### Name and Location Mode

Choose a display name and whether the location should be configured by address or by latitude/longitude.

### Address or Latitude/Longitude

If you choose address mode, provide address line 1, optional address line 2, city, state, and ZIP code.

If you choose latitude/longitude mode, provide coordinates for the protected location.

### Credentials and Endpoints

You may be prompted for:

* Noonlight Client ID
* Noonlight Client Secret
* Noonlight API Endpoint
* Token Endpoint
* Phone number
* PIN
* Secondary contact information
* Additional instructions

Production API endpoint example:

```text
https://api.noonlight.com/platform/v1
```

Sandbox API endpoint example:

```text
https://api-sandbox.noonlight.com/dispatch/v1
```

Token endpoint example:

```text
https://noonlight.konnected.io/ha/token
```

## Home Assistant Events

This integration fires Home Assistant events that can be used in automations, logging systems, dashboards, and notification routing workflows.

### `noonlight_alarm_attempted`

Fired whenever the integration attempts to create (trigger) a Noonlight alarm.

### `noonlight_alarm_created`

Fired when the external Noonlight service successfully creates an active alarm in response to the above creation.

### `noonlight_alarm_failed`

Fired when alarm creation fails.

### `noonlight_webhook_received`

Fired whenever the integration receives an inbound webhook from the external Noonlight service.

## Recommended Home Assistant Helper Architecture

Many advanced Home Assistant users may prefer to separate TEST and LIVE dispatch behavior using Home Assistant helpers and automations.

A common approach is to create helper entities such as:

* Alarm Mode selector
* Noonlight Endpoint Mode selector
* Sandbox token helper
* Production endpoint helper
* Sandbox endpoint helper
* Notification routing helpers
* Dispatch enable/disable switches

Example helper concepts:

```text
Alarm Mode:
  LIVE
  Test
  Test Sensors/Messages

Noonlight Endpoint Mode:
  Production
  Sandbox
```

Home Assistant automations can then dynamically control sandbox vs production API endpoints, sandbox server token overrides, notification routing behavior, SMS and voice testing workflows, whether Noonlight dispatches are permitted, and dispatch logging/escalation workflows.

This allows users to safely test alarm automations without live dispatches, validate notification routing, verify sensor behavior, simulate intrusion/fire/medical workflows, separate sandbox and production credentials, and implement fail-closed production safety protections.

Example override fields used when calling `noonlight.create_alarm`:

```yaml
api_endpoint_override:
token_endpoint_override:
server_token_override:
```

This fork was designed to support automation-driven workflows where dispatch behavior, notification routing, testing modes, and safety protections are controlled externally by Home Assistant logic rather than hardcoded directly inside the integration.

## Service: `noonlight.create_alarm`

This integration exposes the following Home Assistant service:

```text
noonlight.create_alarm
```

## Police Alarm Examples

### Simple Police Example

```yaml
service: noonlight.create_alarm
data:
  service: police
```

### Advanced Police Example

```yaml
service: noonlight.create_alarm
data:
  service: police
  alarm_cause: Garage entry door opened while armed away
  instructions: >
    Residential intrusion alarm.
    Alarm armed in Away mode.
    Homeowner not expected on premises.
    Garage entry door sensor triggered followed by mud room motion.
    Rear driveway accessible from side street.
    Contact homeowner before dispatch if possible.
```

## Fire Alarm Examples

### Simple Fire Example

```yaml
service: noonlight.create_alarm
data:
  service: fire
```

### Advanced Fire Example

```yaml
service: noonlight.create_alarm
data:
  service: fire
  alarm_cause: Basement smoke detector activated
  instructions: >
    Smoke detector triggered in basement utility room near furnace.
    Occupants evacuating structure.
    Rear basement entrance accessible from driveway.
    Homeowner responding.
```

## Medical Alarm Examples

### Simple Medical Example

```yaml
service: noonlight.create_alarm
data:
  service: medical
```

### Advanced Medical Example

```yaml
service: noonlight.create_alarm
data:
  service: medical
  alarm_cause: Medical alert button pressed by homeowner
  instructions: >
    Homeowner requested medical assistance.
    Front door may be unlocked for responders.
    Emergency contact responding to property.
```

## Extended Dispatch Examples

### Simple Extended Example

```yaml
service: noonlight.create_alarm
data:
  service: police
  alarm_cause: Front door intrusion detected
  instructions: Residential alarm. Contact homeowner before dispatch.
```

### Advanced Extended Example

```yaml
service: noonlight.create_alarm
data:
  service: police
  alarm_cause: Multiple intrusion sensors triggered while armed away
  instructions: >
    Alarm armed in Away mode.
    Basement window vibration sensor triggered followed by family room motion.
    No occupants expected home.
    Exterior cameras active.
    Contact homeowner before dispatch if possible.
    Responding officers may use front driveway entrance.
```

## Sandbox Testing Examples

### Simple Sandbox Example

```yaml
service: noonlight.create_alarm
data:
  service: police
  alarm_cause: TEST alarm only
  instructions: TEST ONLY. DO NOT DISPATCH.
  api_endpoint_override: https://api-sandbox.noonlight.com/dispatch/v1
  token_endpoint_override: https://noonlight.konnected.io/ha/token
  server_token_override: YOUR_SANDBOX_SERVER_TOKEN
```

### Advanced Sandbox Example

```yaml
service: noonlight.create_alarm
data:
  service: police
  alarm_cause: TEST intrusion workflow validation
  instructions: >
    TEST ONLY.
    DO NOT DISPATCH.
    Validating Home Assistant automation routing,
    notification sequencing,
    webhook handling,
    dispatch event logging,
    and production safety protections.
  api_endpoint_override: https://api-sandbox.noonlight.com/dispatch/v1
  token_endpoint_override: https://noonlight.konnected.io/ha/token
  server_token_override: YOUR_SANDBOX_SERVER_TOKEN
```

## Sandbox vs Production

This fork adds explicit protections intended to reduce accidental production dispatches.

### Sandbox Safety Checks

If the integration detects a sandbox API endpoint but no sandbox server token override is supplied, the dispatch will fail closed.

### Production Safety Checks

If the integration detects a production API endpoint while a sandbox server token override is present, the dispatch will fail closed.

These protections are intended to reduce accidental live dispatches during testing.

Advanced users may also add their own helper-driven safety rules, such as allowing only these combinations:

```text
Alarm Mode = Test  + Endpoint Mode = Sandbox
Alarm Mode = LIVE  + Endpoint Mode = Production
```

and blocking these dangerous combinations:

```text
Alarm Mode = Test  + Endpoint Mode = Production
Alarm Mode = LIVE  + Endpoint Mode = Sandbox
```

## Webhook Support

This fork includes an optional webhook receiver.

The integration registers a fixed Home Assistant webhook ID:

```text
noonlight_dispatch_events
```

The public webhook URL format is:

```text
https://YOUR_HOME_ASSISTANT_DOMAIN/api/webhook/noonlight_dispatch_events
```

Webhook settings are intentionally not shown in the normal Reconfigure screen. The integration owns the webhook endpoint internally, and users normally configure the public URL in Noonlight or in whatever Noonlight developer/dashboard workflow is being used.

The intent is to keep these responsibilities separate:

* The integration receives inbound Noonlight webhook payloads.
* Home Assistant events expose the payload to automations.
* Home Assistant helpers and automations decide whether to notify, log, escalate, or ignore the webhook.

When a webhook is received, the integration fires:

```text
noonlight_webhook_received
```

Webhook behavior may vary depending on Noonlight account configuration, sandbox vs production behavior, Dispatch API behavior, and Tasks/Verification API behavior.

### Local Webhook Test

You can test the Home Assistant webhook receiver locally from the Home Assistant terminal:

```bash
curl -i -X POST \
  -H "Content-Type: application/json" \
  -d '{"event":"manual_test","status":"ok","source":"curl","message":"Noonlight webhook test from Home Assistant terminal"}' \
  http://127.0.0.1:8123/api/webhook/noonlight_dispatch_events
```

Expected response:

```text
HTTP/1.1 200 OK
OK
```

A successful test should also fire the Home Assistant event `noonlight_webhook_received`.

## Recommended Webhook Helper Architecture

Advanced users may want helpers that control how webhook payloads are handled.

Example helper concepts:

```text
Webhook SMS Enabled:
  on/off

Webhook Persistent Notification Enabled:
  on/off

Webhook Influx Logging Enabled:
  on/off

Webhook Debug Mode:
  on/off
```

This allows users to decide whether webhook events should create persistent notifications, send SMS messages, write to InfluxDB, trigger dashboards, or remain silent except for logs.

## Example Webhook Automations

### Persistent Notification on Webhook Receipt

```yaml
- alias: Noonlight Webhook - Persistent Notification
  trigger:
    - platform: event
      event_type: noonlight_webhook_received
  action:
    - service: persistent_notification.create
      data:
        title: Noonlight Webhook Received
        message: >
          Noonlight sent a webhook.
          Webhook ID: {{ trigger.event.data.webhook_id | default('unknown') }}
          Event: {{ trigger.event.data.payload.event | default('unknown') }}
          Payload: {{ trigger.event.data.payload | default({}) }}
```

### Conditional SMS Notification on Webhook Receipt

```yaml
- alias: Noonlight Webhook - Optional SMS
  trigger:
    - platform: event
      event_type: noonlight_webhook_received
  condition:
    - condition: state
      entity_id: input_boolean.noonlight_webhook_sms_enabled
      state: "on"
  action:
    - service: notify.mobile_app_your_phone
      data:
        title: Noonlight Webhook Received
        message: >
          Noonlight webhook received.
          Event={{ trigger.event.data.payload.event | default('unknown') }}
```

### Logging Webhook Events to InfluxDB

```yaml
- alias: Noonlight Webhook - Influx Logging
  trigger:
    - platform: event
      event_type: noonlight_webhook_received
  condition:
    - condition: state
      entity_id: input_boolean.noonlight_webhook_influx_logging_enabled
      state: "on"
  action:
    - service: influxdb.write
      data:
        measurement: noonlight_webhook
        tags:
          webhook_id: "{{ trigger.event.data.webhook_id | default('unknown') }}"
          event: "{{ trigger.event.data.payload.event | default('unknown') }}"
        fields:
          payload: "{{ trigger.event.data.payload | to_json }}"
```

## Example Home Assistant Automations

### Trigger Noonlight From Alarmo

#### Simple Example

```yaml
automation:
  - alias: Trigger Noonlight From Alarmo
    trigger:
      - platform: state
        entity_id: alarm_control_panel.home_alarm
        to: triggered
    action:
      - service: noonlight.create_alarm
        data:
          service: police
          alarm_cause: Alarmo intrusion alarm triggered
```

#### Advanced Example

```yaml
automation:
  - alias: Trigger Noonlight From Alarmo
    trigger:
      - platform: state
        entity_id: alarm_control_panel.home_alarm
        to: triggered
    action:
      - service: noonlight.create_alarm
        data:
          service: police
          alarm_cause: >
            Alarm armed Away. Mud room storm door opened followed by kitchen motion.
          instructions: >
            Residential intrusion alarm.
            Homeowner not expected on premises.
            Exterior cameras active.
            Contact homeowner before dispatch if possible.
```

### Smoke Alarm Example

#### Simple Example

```yaml
automation:
  - alias: Trigger Noonlight Fire Dispatch
    trigger:
      - platform: state
        entity_id: binary_sensor.smoke_alarm
        to: "on"
    action:
      - service: noonlight.create_alarm
        data:
          service: fire
          alarm_cause: Smoke alarm detected
```

#### Advanced Example

```yaml
automation:
  - alias: Trigger Noonlight Fire Dispatch
    trigger:
      - platform: state
        entity_id: binary_sensor.basement_smoke_detector
        to: "on"
    action:
      - service: noonlight.create_alarm
        data:
          service: fire
          alarm_cause: Basement utility room smoke detector activated
          instructions: >
            Smoke detector activated near furnace and electrical panel.
            Occupants evacuating structure.
            Rear basement entrance accessible from driveway.
            Homeowner responding.
```

## Example Advanced Alarm Routing Architecture

Advanced users may choose to integrate this fork alongside:

* Alarmo
* Twilio
* Home Assistant helpers
* InfluxDB
* Grafana
* Persistent notifications
* Logbook
* Voice call automations
* SMS escalation workflows
* Household notification routing

Example workflows may include TEST vs LIVE dispatch modes, sandbox vs production endpoint separation, dispatch deduplication windows, family escalation sequencing, voice call escalation, SMS queueing, inbound webhook event handling, dashboard monitoring, and automated dispatch logging.

This integration is intentionally designed to integrate cleanly with broader Home Assistant automation ecosystems.

## Recommended Testing Workflow

### 1. Configure Sandbox Mode First

Before enabling production dispatching, thoroughly test your complete workflow in the Noonlight Sandbox environment.

Recommended sandbox validation steps:

* Verify SMS notifications
* Verify voice call notifications
* Verify Home Assistant events
* Verify Home Assistant automations
* Verify dispatch instructions
* Verify address information
* Verify cancellation and PIN workflows
* Verify sandbox endpoint selection
* Verify sandbox token handling
* Verify production safety protections
* Verify notification routing
* Verify logging and diagnostics
* Verify fail-safe behavior during errors
* Verify webhook event handling

### 2. Test Production Carefully

Once sandbox testing is fully validated, production testing should be approached cautiously.

Repeat the same categories of testing in production while carefully coordinating with all affected household members, emergency contacts, and monitoring workflows.

Always notify anyone who may receive alarm calls or SMS alerts before testing.

## Recommended Production Readiness Checklist

Before relying on LIVE dispatch behavior, verify:

* Address information is correct
* PIN information is correct
* Phone numbers are correct
* Sandbox testing completed successfully
* SMS notifications work correctly
* Voice call notifications work correctly
* Webhook handling works correctly
* Home Assistant automations behave correctly
* TEST vs LIVE helper protections work correctly
* Sandbox vs production protections work correctly
* Deduplication logic works correctly
* Internet connectivity is stable
* Household members understand testing procedures
* Notification escalation routing works correctly
* Alarm cancellation workflows are understood

## Notification Routing and Dedicated Alarm Numbers

Many users may prefer to use a dedicated phone number and messaging workflow for alarm-related notifications and testing.

While this integration itself does not require Twilio, VoIP services, or any specific SMS provider, advanced Home Assistant users may choose to integrate additional notification systems such as Twilio, VoIP providers, SMS gateways, Home Assistant mobile notifications, voice call automations, and family notification routing workflows.

Using a dedicated alarm notification number can separate alarm traffic from personal messaging, simplify testing workflows, make alarm calls and texts immediately recognizable, allow independent SMS/call routing automations, help coordinate household notifications, and allow centralized logging and auditing.

## Logging and Diagnostics

This fork is intended to integrate cleanly with Home Assistant automations, persistent notifications, system log, Logbook, InfluxDB, Grafana, Twilio notification routing, and Alarmo.

The integration intentionally fires Home Assistant events instead of forcing hardcoded notification behavior.

## Known Limitations

* Requires internet connectivity
* Requires Noonlight service availability
* Requires Home Assistant availability
* Dispatch behavior depends on Noonlight systems
* Sandbox behavior may differ from production
* Webhook behavior may differ between Noonlight products/APIs
* Not officially supported by Noonlight
* Not officially supported by Konnected
* Not officially supported by Home Assistant

## Credits

Original integration concept and implementation:

* Konnected
* Original Noonlight Home Assistant integration contributors

This repository is a community-maintained fork intended to modernize and extend functionality.

## Related Links

### Noonlight

[https://noonlight.com](https://noonlight.com)

### Noonlight API Docs

[https://docs.noonlight.com](https://docs.noonlight.com)

### Konnected

[https://konnected.io](https://konnected.io)

### Home Assistant

[https://www.home-assistant.io](https://www.home-assistant.io)

## Terms and Liability

Please read and understand the following:

### Noonlight Terms

[https://noonlight.com/terms](https://noonlight.com/terms)

### Konnected Terms

[https://konnected.io/terms](https://konnected.io/terms)

### Home Assistant Terms

[https://www.home-assistant.io/tos/](https://www.home-assistant.io/tos/)

By using this software, you acknowledge that:

* You are responsible for testing your system
* You are responsible for understanding your automations
* You are responsible for validating all emergency contact information
* You are responsible for all dispatch outcomes
* This software may fail
* False alarms may occur
* Emergency dispatches may fail or be delayed

Use entirely at your own risk.
