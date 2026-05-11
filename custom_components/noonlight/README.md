# Noonlight Enhanced for Home Assistant

## Overview

This is an unofficial Home Assistant custom integration for the Noonlight Dispatch API.

It is based on the original Noonlight Home Assistant integration project and has been significantly extended to support modern Noonlight Dispatch API workflows, sandbox testing, Home Assistant event generation, webhook integrations, richer dispatch context, improved diagnostics, and advanced Home Assistant automation architectures.

As stated in the original integration:

> "Noonlight connects to emergency 9-1-1 services in all 50 U.S. states. Backed by a UL-compliant alarm monitoring center and staffed 24/7 with live operators in the United States, Noonlight is standing by to send help to your home at a moment's notice."

(Currently this service is only available in the United States.)

This fork focuses heavily on:

* Safer testing workflows
* Sandbox vs production separation
* Richer dispatch information
* Better Home Assistant automation integration
* Improved observability and diagnostics
* Advanced routing and notification workflows
* Fail-closed operational safety protections

---

# What Changed in This Fork

The original integration only supported very minimal dispatch context consisting primarily of:

* Police
* Fire
* Medical

This fork modernizes and significantly extends the integration to support newer Noonlight Dispatch API workflows and much richer automation-driven dispatch context.

Major additions include:

* Noonlight Dispatch API v2-compatible workflow support
* Sandbox testing support
* Sandbox server token override support
* Production vs sandbox safety protections
* Rich human-readable alarm context support
* Alarm cause support
* Dispatch instruction support
* Home Assistant dispatch lifecycle events
* Webhook receiver support
* Improved logging and diagnostics
* Better Home Assistant automation integration
* Cleaner notification architecture
* Improved failure handling
* API endpoint override support
* Token endpoint override support
* Home Assistant event-driven automation workflows

This allows Home Assistant automations to provide significantly more useful dispatch information such as:

* Which sensor triggered
* Which room or area was involved
* Whether the alarm was intrusion, fire, or medical related
* Whether the alarm is TEST or LIVE
* Occupancy context
* Human-readable alarm descriptions
* Additional automation-generated situational context
* Dispatcher instructions
* Property access information
* Contact workflows

Examples:

* “Mud room storm door at rear of home opened while system armed Away.”
* “Smoke detector activated in basement utility room near furnace.”
* “Medical alert button pressed by homeowner.”
* “TEST ONLY. DO NOT DISPATCH.”

The goal is to provide monitoring operators and first responders with clearer situational awareness at the exact same time the alarm is created.

This fork is intended for advanced Home Assistant users who want deeper control, testing, automation, observability, and routing flexibility around Noonlight dispatch workflows.

---

# Important Safety Notice

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

# Features

## Core Features

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

## Extended Features Added in This Fork

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
* Better Home Assistant automation integration
* Removal of hardcoded notification behavior
* Cleaner event-driven architecture

---

# Home Assistant Events

This integration fires Home Assistant events that can be used in automations, logging systems, dashboards, and notification routing workflows.

## Events

### `noonlight_alarm_attempted`

Fired whenever the integration attempts to create a Noonlight alarm.

### `noonlight_alarm_created`

Fired when Noonlight successfully creates an ACTIVE alarm.

### `noonlight_alarm_failed`

Fired when alarm creation fails.

### `noonlight_webhook_received`

Fired whenever the integration receives an inbound Noonlight webhook.

---

# Installation

## HACS Installation

1. Open HACS
2. Go to Integrations
3. Open the menu in the upper-right corner
4. Select Custom Repositories
5. Add this repository URL:

```text
https://github.com/KruseLuds/noonlight-hass
```

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

# Initial Noonlight Setup

Before configuring the integration, you should:

1. Create a Noonlight account
2. Create or obtain Noonlight developer/API credentials
3. Determine whether you will initially test using Sandbox or Production
4. Decide how you want Home Assistant automations to control testing vs live dispatch behavior

You will typically need:

* Noonlight Client ID
* Noonlight Client Secret
* A U.S.-based phone number
* Address information
* PIN information
* Home Assistant
* Internet connectivity

Depending on your setup, you may use:

* Production Noonlight Dispatch API endpoints
* Sandbox Noonlight Dispatch API endpoints
* Sandbox server token overrides

The original integration architecture uses Konnected-hosted token broker endpoints to obtain Noonlight access tokens.

---

# Configuration

After installation:

1. Open Home Assistant
2. Go to Settings → Devices & Services
3. Add Integration
4. Search for Noonlight

You will be prompted for:

## Noonlight Client ID

Client identifier associated with your Noonlight application.

## Noonlight Client Secret

Client secret associated with your Noonlight application.

## Noonlight API Endpoint

Examples:

### Production

```text
https://api.noonlight.com/platform/v1
```

### Sandbox

```text
https://api-sandbox.noonlight.com/dispatch/v1
```

## Token Endpoint

Example:

```text
https://noonlight.konnected.io/ha/token
```

## Address Information

* Address line 1
* Address line 2
* City
* State
* ZIP code

## Contact Information

* Name
* Phone number
* PIN

Optional:

* Secondary contact
* Secondary phone
* Additional instructions

---

# Recommended Home Assistant Helper Architecture

Many advanced Home Assistant users may prefer to separate TEST and LIVE dispatch behavior using Home Assistant helpers and automations.

A common approach is to create Home Assistant helper entities such as:

* Alarm Mode selector
* Noonlight Endpoint Mode selector
* Sandbox token helper
* Production token helper
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

Home Assistant automations can then dynamically control:

* Sandbox vs production API endpoints
* Sandbox server token overrides
* Notification routing behavior
* SMS and voice testing workflows
* Whether Noonlight dispatches are actually permitted
* Dispatch logging and escalation workflows

This allows Home Assistant users to:

* Safely test alarm automations without live dispatches
* Validate notification routing
* Verify sensor behavior
* Simulate intrusion, fire, and medical workflows
* Separate sandbox and production credentials
* Implement fail-closed production safety protections
* Create household-specific escalation workflows
* Add centralized logging and diagnostics

Example override concepts:

```yaml
api_endpoint_override:
token_endpoint_override:
server_token_override:
```

when calling:

```yaml
service: noonlight.create_alarm
```

This fork was specifically designed to support advanced Home Assistant automation-driven workflows where dispatch behavior, notification routing, testing modes, and safety protections are controlled externally by Home Assistant logic rather than hardcoded directly inside the integration.

---

# Service: noonlight.create_alarm

This integration exposes the following Home Assistant service:

```text
noonlight.create_alarm
```

---

# Police Alarm Examples

## Simple Police Example

```yaml
service: noonlight.create_alarm
data:
  service: police
```

## Advanced Police Example

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

---

# Fire Alarm Examples

## Simple Fire Example

```yaml
service: noonlight.create_alarm
data:
  service: fire
```

## Advanced Fire Example

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

---

# Medical Alarm Examples

## Simple Medical Example

```yaml
service: noonlight.create_alarm
data:
  service: medical
```

## Advanced Medical Example

```yaml
service: noonlight.create_alarm
data:
  service: medical
  alarm_cause: Medical alert button pressed by homeowner
  instructions: >
    Elderly homeowner requested medical assistance.
    Front door may be unlocked for responders.
    Emergency contact responding to property.
```

---

# Extended Dispatch Examples

## Simple Extended Example

```yaml
service: noonlight.create_alarm
data:
  service: police
  alarm_cause: Front door intrusion detected
  instructions: Residential alarm. Contact homeowner before dispatch.
```

## Advanced Extended Example

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

---

# Sandbox Testing Examples

## Simple Sandbox Example

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

## Advanced Sandbox Example

```yaml
service: noonlight.create_alarm
data:
  service: police
  alarm_cause: TEST intrusion workflow validation
  instructions: >
    TEST ONLY.
    DO NOT DISPATCH.
    Validating Home Assistant automation routing,
    Twilio notification sequencing,
    webhook handling,
    dispatch event logging,
    and production safety protections.
  api_endpoint_override: https://api-sandbox.noonlight.com/dispatch/v1
  token_endpoint_override: https://noonlight.konnected.io/ha/token
  server_token_override: YOUR_SANDBOX_SERVER_TOKEN
```

---

# Sandbox vs Production

This fork adds explicit protections intended to reduce accidental production dispatches.

## Sandbox Safety Checks

If the integration detects a sandbox API endpoint but no sandbox server token override is supplied, the dispatch will fail closed.

## Production Safety Checks

If the integration detects a production API endpoint while a sandbox server token override is present, the dispatch will fail closed.

These protections were added specifically to reduce accidental live dispatches during testing.

---

# Webhook Support

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

# Example Home Assistant Automations

## Trigger Noonlight From Alarmo

### Simple Example

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

### Advanced Example

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

---

## Smoke Alarm Example

### Simple Example

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

### Advanced Example

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

---

# Example Advanced Alarm Routing Architecture

Many advanced Home Assistant users may choose to integrate this fork alongside:

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

Example advanced workflows may include:

* TEST vs LIVE dispatch modes
* Sandbox vs production endpoint separation
* Dispatch deduplication windows
* Family escalation sequencing
* Voice call escalation
* SMS queueing
* Inbound webhook event handling
* Dashboard-based operational monitoring
* Automated dispatch logging and auditing

This integration is intentionally designed to integrate cleanly with broader Home Assistant automation ecosystems.

---

# Recommended Testing Workflow

## 1. Configure Sandbox Mode First

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
* Verify webhook event handling

## 2. Only Then Test Production Carefully

Once Sandbox testing is fully validated, production testing should be approached cautiously.

Repeat the same categories of testing above in production while carefully coordinating with all affected household members, emergency contacts, and monitoring workflows.

Always notify anyone who may receive alarm calls before testing.

Always notify anyone who may receive SMS alerts before testing.

---

# Recommended Production Readiness Checklist

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

---

# Notification Routing and Dedicated Alarm Numbers

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

---

# Logging and Diagnostics

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

# Known Limitations

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

# Credits

Original integration concept and implementation:

* Konnected
* Original Noonlight Home Assistant integration contributors

This repository is a community-maintained fork intended to modernize and extend functionality.

---

# Related Links

## Noonlight

[https://noonlight.com](https://noonlight.com)

## Noonlight API Docs

[https://docs.noonlight.com](https://docs.noonlight.com)

## Konnected

[https://konnected.io](https://konnected.io)

## Home Assistant

[https://www.home-assistant.io](https://www.home-assistant.io)

---

# Terms and Liability

Please read and understand the following:

## Noonlight Terms

[https://noonlight.com/terms](https://noonlight.com/terms)

## Konnected Terms

[https://konnected.io/terms](https://konnected.io/terms)

## Home Assistant Terms

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
