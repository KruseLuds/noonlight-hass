"""Tests for noonlight.cancel_alarm.

Runs the integration against a fake Noonlight Dispatch API and token broker on
localhost, over real HTTP, so the real `noonlight` client is exercised.
Sandbox vs production is detected from the endpoint URL, so the fake server
serves both under path prefixes that contain the real hostnames.

    pip install homeassistant noonlight pytest
    pytest tests
"""
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import aiohttp
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import homeassistant.util.dt as dt_util  # noqa: E402
from homeassistant import core  # noqa: E402
from homeassistant.core import callback  # noqa: E402
from homeassistant.helpers import issue_registry as ir  # noqa: E402

from custom_components import noonlight as integ  # noqa: E402

SANDBOX = "api-sandbox.noonlight.com/dispatch/v1"
PRODUCTION = "api.noonlight.com/dispatch/v1"


class FakeNoonlight:
    """Fake token broker + Dispatch API. Records every request."""

    def __init__(self):
        self.requests = []          # (path, authorization, body)
        self.valid_tokens = {"SBTOKEN", "DEVTOKEN"}
        self.issued = 0
        self.token_lifetime = timedelta(hours=24)
        self.status_response = None  # override the cancel response body
        self.alarms = 0
        self.reject_all = False      # every token gets 401
        self.delay = 0               # seconds before the broker / cancel answer

    async def token(self, request):
        await asyncio.sleep(self.delay)
        body = await request.json()
        self.requests.append((request.path, None, body))
        self.issued += 1
        token = f"TOKEN{self.issued}"
        self.valid_tokens.add(token)
        return web.json_response({"token": token,
                                  "expires": (dt_util.utcnow() + self.token_lifetime).isoformat()})

    def _auth_ok(self, request):
        return (not self.reject_all
                and request.headers.get("Authorization", "").removeprefix("Bearer ") in self.valid_tokens)

    async def create(self, request):
        body = await request.json()
        self.requests.append((request.path, request.headers.get("Authorization"), body))
        if not self._auth_ok(request):
            return web.json_response({"message": "Unauthorized"}, status=401)
        self.alarms += 1
        return web.json_response({"id": f"A{self.alarms}", "status": "ACTIVE",
                                  "created_at": "2026-01-01T00:00:00Z"}, status=201)

    async def status(self, request):
        await asyncio.sleep(self.delay)
        body = await request.json()
        self.requests.append((request.path, request.headers.get("Authorization"), body))
        if not self._auth_ok(request):
            return web.json_response({"message": "Unauthorized"}, status=401)
        if body.get("pin") != "1234":
            return web.json_response({"code": 400, "message": "Bad Request",
                                      "details": "Provided PIN is invalid or incorrect"}, status=400)
        return web.json_response(self.status_response or
                                 {"status": "CANCELED", "created_at": "2026-01-01T00:00:00Z"}, status=201)

    def status_posts(self):
        return [r for r in self.requests if r[0].endswith("/status")]


class Harness:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self.fake = FakeNoonlight()
        self.events = []

    async def __aenter__(self):
        app = web.Application()
        app.router.add_post("/token", self.fake.token)
        for env in (SANDBOX, PRODUCTION):
            app.router.add_post(f"/{env}/alarms", self.fake.create)
            app.router.add_post(f"/{env}/alarms/{{alarm_id}}/status", self.fake.status)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        self.base = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}"
        self.session = aiohttp.ClientSession()
        self.patch = patch.object(integ, "async_get_clientsession", lambda hass: self.session)
        self.patch.start()
        self.hass = core.HomeAssistant(str(self.tmp_path))
        await ir.async_load(self.hass)
        # @callback: runs in the event loop in firing order. A plain function
        # would run in a thread pool and could record events out of order.
        @callback
        def record(event):
            self.events.append((event.event_type, dict(event.data)))

        for event in ("noonlight_alarm_created", "noonlight_alarm_canceled", "noonlight_alarm_failed"):
            self.hass.bus.async_listen(event, record)
        return self

    async def __aexit__(self, *exc):
        await self.hass.async_block_till_done()
        await self.hass.async_stop(force=True)
        self.patch.stop()
        await self.session.close()
        await self.runner.cleanup()

    def url(self, env):
        return f"{self.base}/{env}"

    def config(self, env=PRODUCTION, **extra):
        return {"id": "cid", "secret": "csecret", "api_endpoint": self.url(env),
                "token_endpoint": f"{self.base}/token", "address1": "1 Main St", "city": "X",
                "state": "FL", "zip": "00000", "name": "Owner", "phone": "15555550100",
                "pin": "1234", **extra}

    async def integration(self, **config):
        """A fresh integration instance, i.e. what exists after a (re)start."""
        n = integ.NoonlightIntegration(self.hass, config or self.config())
        await n.async_load_alarm_routes()
        return n

    async def last_event(self):
        await self.hass.async_block_till_done()
        return self.events[-1]


def run(coro):
    asyncio.run(coro)


async def created_id(h):
    await h.hass.async_block_till_done()
    return [d for t, d in h.events if t == "noonlight_alarm_created"][-1]["alarm_id"]


# --- routing ------------------------------------------------------------------

def test_sandbox_alarm_cancelled_in_sandbox_with_its_token(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()  # configured for PRODUCTION
            assert await n.create_alarm(alarm_types=["police"], api_endpoint_override=h.url(SANDBOX),
                                        server_token_override="SBTOKEN")
            alarm_id = (await created_id(h))
            assert await n.cancel_alarm(alarm_id=alarm_id)
            path, auth, body = h.fake.status_posts()[-1]
            assert path == f"/{SANDBOX}/alarms/{alarm_id}/status"
            assert auth == "Bearer SBTOKEN"
            assert body == {"status": "CANCELED", "pin": "1234"}
            assert await h.last_event() == ("noonlight_alarm_canceled", {
                "alarm_id": alarm_id, "api_endpoint": h.url(SANDBOX), "environment": "sandbox"})
    run(go())


def test_production_alarm_with_sandbox_override_fails_closed(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            assert not await n.cancel_alarm(alarm_id=(await created_id(h)), server_token_override="SBTOKEN")
            assert not h.fake.status_posts()
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and data["action"] == "cancel"
    run(go())


# --- confirmation ---------------------------------------------------------------

def test_wrong_pin_fails_and_never_fires_canceled(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            assert not await n.cancel_alarm(alarm_id=(await created_id(h)), pin="0000")
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed"
            assert data["action"] == "cancel" and "PIN" in data["error"]
            assert not [e for e in h.events if e[0] == "noonlight_alarm_canceled"]
    run(go())


def test_unconfirmed_response_is_a_failure(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            h.fake.status_response = {"status": "ACTIVE"}
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            assert not await n.cancel_alarm(alarm_id=(await created_id(h)))
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and "did not confirm" in data["error"]
    run(go())


# --- tokens ---------------------------------------------------------------------

def test_expiring_production_token_is_renewed_before_cancel(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            h.fake.token_lifetime = timedelta(minutes=1)  # under the 5 minute margin
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            created_with = h.fake.issued
            assert await n.cancel_alarm(alarm_id=(await created_id(h)))
            assert h.fake.issued == created_with + 1
            assert h.fake.status_posts()[-1][1] == f"Bearer TOKEN{h.fake.issued}"
    run(go())


def test_valid_production_token_is_reused(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            created_with = h.fake.issued
            assert await n.cancel_alarm(alarm_id=(await created_id(h)))
            assert h.fake.issued == created_with
            assert h.fake.status_posts()[-1][1] == f"Bearer TOKEN{created_with}"
    run(go())


def test_401_renews_once_and_retries(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            h.fake.valid_tokens.discard(f"TOKEN{h.fake.issued}")  # revoked after create
            assert await n.cancel_alarm(alarm_id=(await created_id(h)))
            assert len(h.fake.status_posts()) == 2
            assert (await h.last_event())[0] == "noonlight_alarm_canceled"
    run(go())


def test_second_401_fails(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            alarm_id = await created_id(h)
            h.fake.reject_all = True
            assert not await n.cancel_alarm(alarm_id=alarm_id)
            assert len(h.fake.status_posts()) == 2  # one retry, no more
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and "Unauthorized" in data["error"]
    run(go())


def test_token_renewal_exception_fires_failed_event(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            h.fake.token_lifetime = timedelta(minutes=1)
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])

            async def boom(**kwargs):
                raise RuntimeError("token endpoint exploded")
            n.check_api_token = boom
            assert not await n.cancel_alarm(alarm_id=(await created_id(h)))
            assert not h.fake.status_posts()
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and data["action"] == "cancel"
            assert "renewal failed" in data["error"]
    run(go())


def test_cancel_request_timeout_fires_failed_event(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            alarm_id = await created_id(h)
            h.fake.delay = 2
            with patch.object(integ, "CANCEL_REQUEST_TIMEOUT", timedelta(seconds=0.3)):
                assert not await n.cancel_alarm(alarm_id=alarm_id)
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and data["action"] == "cancel"
            assert "did not answer" in data["error"]
            assert alarm_id in n._alarm_routes  # kept for a retry
    run(go())


def test_token_renewal_timeout_fires_failed_event(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            h.fake.token_lifetime = timedelta(minutes=1)  # forces a renewal at cancel
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            alarm_id = await created_id(h)
            h.fake.delay = 2
            with patch.object(integ, "CANCEL_REQUEST_TIMEOUT", timedelta(seconds=0.3)):
                assert not await n.cancel_alarm(alarm_id=alarm_id)
            assert not h.fake.status_posts()
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and "renewal failed" in data["error"]
    run(go())


def test_token_renewal_failure_fires_failed_event(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            h.fake.token_lifetime = timedelta(minutes=1)
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            n.config = {**n.config, "token_endpoint": f"{h.base}/no-such-endpoint"}
            # the route remembers the original token endpoint; break that one instead
            n._alarm_routes[(await created_id(h))]["token_endpoint"] = f"{h.base}/no-such-endpoint"
            assert not await n.cancel_alarm(alarm_id=(await created_id(h)))
            assert not h.fake.status_posts()
            assert (await h.last_event())[0] == "noonlight_alarm_failed"
    run(go())


# --- restart / environment --------------------------------------------------------

def test_restart_with_changed_config_still_cancels_in_creating_environment(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()  # production
            assert await n.create_alarm(alarm_types=["police"])
            alarm_id = (await created_id(h))
            # restart with the config switched to the sandbox
            n2 = await h.integration(**h.config(env=SANDBOX))
            assert await n2.cancel_alarm(alarm_id=alarm_id)
            path, auth, _ = h.fake.status_posts()[-1]
            assert path == f"/{PRODUCTION}/alarms/{alarm_id}/status"
            assert auth == f"Bearer TOKEN{h.fake.issued}"  # renewed: tokens are not persisted
    run(go())


def test_restart_sandbox_alarm_needs_override(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"], api_endpoint_override=h.url(SANDBOX),
                                        server_token_override="SBTOKEN")
            alarm_id = (await created_id(h))
            n2 = await h.integration()  # restart
            assert not await n2.cancel_alarm(alarm_id=alarm_id)
            assert not h.fake.status_posts()
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and "server_token_override" in data["error"]
            assert await n2.cancel_alarm(alarm_id=alarm_id, server_token_override="SBTOKEN")
            assert h.fake.status_posts()[-1][0] == f"/{SANDBOX}/alarms/{alarm_id}/status"
    run(go())


def test_tokens_are_never_written_to_storage(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"], api_endpoint_override=h.url(SANDBOX),
                                        server_token_override="SBTOKEN")
            assert await n.create_alarm(alarm_types=["police"])
            await h.hass.async_block_till_done()
            stored = (tmp_path / ".storage" / "noonlight.alarm_routes").read_text()
            assert "SBTOKEN" not in stored and "TOKEN" not in stored.replace("token_", "")
            assert set(json.loads(stored)["data"]) == {"A1", "A2"}
    run(go())


# --- bookkeeping ------------------------------------------------------------------

def test_successful_cancel_forgets_the_route(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            alarm_id = (await created_id(h))
            assert await n.cancel_alarm(alarm_id=alarm_id)
            assert alarm_id not in n._alarm_routes
            n2 = await h.integration()
            assert alarm_id not in n2._alarm_routes
    run(go())


def test_stale_routes_are_pruned_on_load(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            fresh = (await created_id(h))
            n._alarm_routes["OLD"] = {**n._alarm_routes[fresh],
                                      "created_at": (dt_util.utcnow() - timedelta(hours=25)).isoformat()}
            await n._async_save_alarm_routes()
            n2 = await h.integration()
            assert "OLD" not in n2._alarm_routes and fresh in n2._alarm_routes
    run(go())


def test_unknown_alarm_id_fails_closed_without_contacting_noonlight(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()  # configured for production
            assert await n.create_alarm(alarm_types=["police"])
            before = len(h.fake.requests)
            assert not await n.cancel_alarm(alarm_id="not-an-alarm-id")
            assert len(h.fake.requests) == before  # nothing sent anywhere
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and "Unknown Noonlight alarm_id" in data["error"]
    run(go())


def test_expired_route_fails_closed(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            alarm_id = await created_id(h)
            n._alarm_routes[alarm_id]["created_at"] = (dt_util.utcnow() - timedelta(hours=25)).isoformat()
            await n._async_save_alarm_routes()
            n2 = await h.integration()  # restart prunes it
            before = len(h.fake.requests)
            assert not await n2.cancel_alarm(alarm_id=alarm_id)
            assert len(h.fake.requests) == before
    run(go())


def test_no_alarm_fails(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert not await n.cancel_alarm(alarm_id=None)
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and data["action"] == "cancel"
    run(go())


def test_missing_alarm_id_fails_without_contacting_noonlight(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])  # an alarm exists
            before = len(h.fake.requests)
            assert not await n.cancel_alarm(alarm_id=None)
            assert not await n.cancel_alarm(alarm_id="")
            assert len(h.fake.requests) == before  # never guesses the latest alarm
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and "needs an alarm_id" in data["error"]
    run(go())


def test_route_expires_while_home_assistant_keeps_running(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            alarm_id = await created_id(h)
            # No restart, no new alarm: only cancel_alarm itself can expire it.
            n._alarm_routes[alarm_id]["created_at"] = (dt_util.utcnow() - timedelta(hours=25)).isoformat()
            before = len(h.fake.requests)
            assert not await n.cancel_alarm(alarm_id=alarm_id)
            assert len(h.fake.requests) == before
            assert alarm_id not in n._alarm_routes
            event, data = await h.last_event()
            assert event == "noonlight_alarm_failed" and "Unknown Noonlight alarm_id" in data["error"]
    run(go())


def test_route_save_failure_still_creates_alarm_and_warns(tmp_path, caplog):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()

            async def broken_save(data):
                raise OSError("disk full")
            with patch.object(n._routes_store, "async_save", broken_save):
                assert await n.create_alarm(alarm_types=["police"])  # still created
            await h.hass.async_block_till_done()
            created = [d for t, d in h.events if t == "noonlight_alarm_created"][-1]
            assert created["restart_safe_cancel"] is False
            issues = ir.async_get(h.hass)
            assert issues.async_get_issue("noonlight", "alarm_routes_not_saved") is not None
            # cancel still works until a restart (route is in memory)
            assert await n.cancel_alarm(alarm_id=created["alarm_id"])
            # next successful save clears the issue and the flag is True again
            assert await n.create_alarm(alarm_types=["police"])
            await h.hass.async_block_till_done()
            assert [d for t, d in h.events if t == "noonlight_alarm_created"][-1]["restart_safe_cancel"] is True
            assert issues.async_get_issue("noonlight", "alarm_routes_not_saved") is None
    run(go())
    assert "cancelling them after a Home Assistant restart is unavailable" in caplog.text


def test_failed_cancel_keeps_the_route_for_a_retry(tmp_path):
    async def go():
        async with Harness(tmp_path) as h:
            n = await h.integration()
            assert await n.create_alarm(alarm_types=["police"])
            alarm_id = (await created_id(h))
            assert not await n.cancel_alarm(alarm_id=alarm_id, pin="0000")
            assert alarm_id in n._alarm_routes
            assert await n.cancel_alarm(alarm_id=alarm_id)
    run(go())
