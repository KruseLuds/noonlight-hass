# Noonlight for Home Assistant

## Overview

This is an unofficial Home Assistant custom integration for the Noonlight Dispatch API.

It is based on the original Noonlight Home Assistant integration project and has been extended to support modern Noonlight Dispatch API workflows, sandbox testing, Home Assistant event generation, improved error handling, and more advanced automation support.

## What Changed in This Fork

This fork allows additional important critical and timely contextual information to be included in alerts such as the sensor name, cause of the alert and instructions for the dispatcher. To do so, it modernizes and extends the original Noonlight Home Assistant integration with a focus on newer Noonlight Dispatch API workflows, improved Home Assistant automation support, safer testing workflows and richer dispatch context.

Major additions include:

- Sandbox Dispatch API support
- Sandbox server token override support
- Production vs sandbox safety protections
- Rich human-readable alarm context support
- Alarm cause and dispatch instruction support
- Home Assistant dispatch lifecycle events
- Webhook receiver support
- Improved logging and diagnostics
- Better Home Assistant automation integration
- Improved failure handling
- Cleaner notification architecture

This fork is intended for advanced Home Assistant users who want deeper control, testing, automation, and observability around Noonlight dispatch workflows.

This project allows Home Assistant automations to request emergency dispatch assistance from Noonlight for:

* Police
* Fire
* Medical

A major enhancement in this fork is support for newer Noonlight Dispatch API workflows that allow significantly richer contextual information to be sent along with an alarm. Instead of sending only a generic alarm signal, Home Assistant automations can now include detailed alarm causes, triggering sensor information, human-readable descriptions, and custom dispatcher instructions.

This allows Noonlight operators to receive substantially more useful context about what actually happened, such as:

* Which sensor triggered
* Which room or area was involved
* Whether the alarm was intrusion, fire, or medical related
* Human-readable trigger descriptions
* Testing vs live dispatch context
* Custom dispatch instructions
* Additional automation-generated situational details

Examples might include:

* “Mud room storm door at back of house was opened.”
* “Smoke detector activated in basement utility room.”
* “Medical alert button pressed by homeowner.”
* “TEST ONLY. DO NOT DISPATCH.”

The goal is to also provide dispatchers and monitoring operators with clearer situational awareness and more nuanced alarm context right at the same time they receive the alert (the previous integration had no test environment available and was only "police/fire/medical" with no other information).

The integration is intended for advanced Home Assistant users who want to integrate professionally monitored dispatch workflows directly into their own automations and alarm systems.

---

## Important Safety Notice

This project is NOT certified life-safety software.

This integration is provided AS IS without warranties of any kind.

Using Home Assistant with Noonlight involves multiple independent systems and providers, including but not limited to:

* Home Assistant
* Your internet provider
* Your networking equipment
* Your cloud or tunnel provider
* Noonlight
* Konnected token services
* Cellular/SMS/voice providers
* Your own automations and scripts

Any of these systems may fail.

You are fully responsible for:

* Testing your automations
* Verifying dispatch behavior
* Validating notifications
* Confirming address and contact information
* Maintaining backup safety systems
* Understanding the risks of false alarms or failed alarms

DO NOT rely solely on this integration for personal safety, fire protection, medical emergencies, or property protection.

Always maintain independent safety measures and test regularly.

---

## Features

### Core Features

* Home Assistant Noonlight integration
* Supports police, fire, and medical dispatch requests
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
* Improved logging
* Removal of hardcoded persistent notification behavior
* Better Home Assistant automation integration

---

## Home Assistant Events

This integration fires Home Assistant events that can be used in automations.

### Events

#### `noonlight_alarm_attempted`

Fired whenever the integration attempts to create a Noonlight alarm.

#### `noonlight_alarm_created`

Fired when Noonlight successfully creates an ACTIVE alarm.

#### `noonlight_alarm_failed`

Fired when alarm creation fails.

#### `noonlight_webhook_received`

Fired whenever the integration receives an inbound Noonlight webhook.

---

## Installation

## HACS Installation

1. Open HACS
2. Go to Integrations
3. Open the menu in the upper right
4. Select Custom Repositories
5. Add this repository URL
6. Category: Integration
7. Install the integration
8. Restart Home Assistant

---

## Manual Installation

Copy the `custom_components/noonlight` folder into your Home Assistant `custom_components` directory:

```text
/config/custom_components/noonlight
```

Then restart Home Assistant.

---

## Initial Noonlight Setup

You will need:

* A Noonlight account
* A U.S.-based phone number
* Home Assistant
* Internet connectivity

The original integration architecture uses Konnected-hosted token broker endpoints to obtain Noonlight access tokens.

Depending on your setup, you may use:

* Production Noonlight Dispatch API endpoints
* Sandbox Noonlight Dispatch API endpoints
* Sandbox server token overrides

---

## Configuration

After installation:

1. Open Home Assistant
2. Go to Settings → Devices & Services
3. Add Integration
4. Search for Noonlight

You will be prompted for:

### Noonlight ID

Noonlight integration identifier.

### Noonlight Secret

Secret associated with the Noonlight integration ID.

### Noonlight API Endpoint

Examples:

Production:

```text
https://api.noonlight.com/platform/v1
```

Sandbox:

```text
https://api-sandbox.noonlight.com/dispatch/v1
```

### Token Endpoint

Examples:

```text
https://noonlight.konnected.io/ha/token
```

### Address Information

* Address line 1
* Address line 2
* City
* State
* ZIP code

### Contact Information

* Name
* Phone number
* PIN

Optional:

* Secondary contact
* Secondary phone

---

## Service: noonlight.create_alarm

This integration exposes the following Home Assistant service:

```text
noonlight.create_alarm
```

---

## Basic Example

```yaml
service: noonlight.create_alarm
data:
  service: police
```

---

## Fire Alarm Example

```yaml
service: noonlight.create_alarm
data:
  service: fire
```

---

## Medical Alarm Example

```yaml
service: noonlight.create_alarm
data:
  service: medical
```

---

## Extended Dispatch Example

```yaml
service: noonlight.create_alarm
data:
  service: police
  alarm_cause: Front door intrusion detected
  instructions: Residential alarm. Contact homeowner before dispatch.
```

---

## Sandbox Testing Example

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

---

## Sandbox vs Production

This fork adds explicit protections intended to reduce accidental production dispatches.

### Sandbox Safety Checks

If the integration detects a sandbox API endpoint but no sandbox server token override is supplied, the dispatch will fail closed.

### Production Safety Checks

If the integration detects a production API endpoint while a sandbox server token override is present, the dispatch will fail closed.

These protections were added specifically to reduce the chance of accidental live dispatches during testing.

---

## Webhook Support

This fork includes optional webhook receiver support.

Webhook endpoint format:

```text
https://YOUR_HOME_ASSISTANT_DOMAIN/api/webhook/noonlight_dispatch_events
```

Webhook behavior may vary depending on:

* Noonlight account configuration
* Sandbox vs production behavior
* Noonlight Dispatch API behavior
* Noonlight Tasks/Verification API behavior

Webhook payload handling is intentionally minimal by default and is intended to be integrated into Home Assistant automations.

---

## Example Home Assistant Automations

### Trigger Noonlight From Alarmo

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

---

### Smoke Alarm Example

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

---

## Recommended Testing Workflow

### 1. Configure Sandbox Mode First

Before enabling production dispatching, thoroughly test your complete workflow in the Noonlight Sandbox environment.

Recommended Sandbox validation steps:

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

### 2. Only Then Test Production Carefully

Once Sandbox testing is fully validated, production testing should be approached cautiously.

Repeat the same categories of testing above in production, while carefully coordinating with all affected household members, emergency contacts, and monitoring workflows.

Always notify anyone who may receive alarm calls before testing.

Always notify anyone who may receive SMS alerts before testing.

---

## Notification Routing and Dedicated Alarm Numbers

Many users may prefer to use a dedicated phone number and messaging workflow for alarm-related notifications and testing.

While this integration itself does not require Twilio, VoIP services, or any specific SMS provider, advanced Home Assistant users may choose to integrate additional notification systems such as:

* Twilio
* VoIP providers
* SMS gateways
* Home Assistant mobile notifications
* Voice call automations
* Family notification routing workflows

Using a dedicated alarm notification number can provide several advantages:

* Separates alarm traffic from personal messaging
* Simplifies testing workflows
* Makes alarm calls and texts immediately recognizable
* Allows independent SMS/call routing automations
* Helps coordinate household notifications
* Allows centralized logging and auditing

This integration is intentionally designed to work well alongside Home Assistant automation systems that provide additional notification routing, escalation, logging, and diagnostic functionality.

## Logging and Diagnostics

This fork is intended to integrate cleanly with:

* Home Assistant automations
* Persistent notifications
* System log
* Logbook
* InfluxDB
* Grafana
* Twilio notification routing
* Alarmo

The integration intentionally fires Home Assistant events instead of forcing hardcoded notification behavior.

---

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

---

## Credits

Original integration concept and implementation:

* Konnected
* Original Noonlight Home Assistant integration contributors

This repository is a community-maintained fork intended to modernize and extend functionality.

---

## Related Links

### Noonlight

[https://noonlight.com](https://noonlight.com)

### Noonlight API Docs

[https://docs.noonlight.com](https://docs.noonlight.com)

### Konnected

[https://konnected.io](https://konnected.io)

### Home Assistant

[https://www.home-assistant.io](https://www.home-assistant.io)

---

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
