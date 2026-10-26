import asyncio
import ssl
from typing import Any, Final, Optional

from httpx import AsyncClient, HTTPError, Timeout
from loguru import logger
from remnapy import RemnawaveSDK

from src.application.common import FleetProber, PanelFleet
from src.application.dto import PanelHostDto, ProbeQuotaDto, ProbeResultDto, ProbeTargetDto
from src.application.services.fleet import CHECK_PROBE_BUDGET
from src.core.config import AppConfig


class RemnaPanelFleet(PanelFleet):
    """Hosts and the subscription announce of the panel.

    Talks to the REST API directly instead of going through the SDK models: those are
    generated for one panel version and reject responses of a newer one, while the few
    fields used here have been stable.
    """

    ANNOUNCE_HEADER: Final[str] = "announce"
    # the panel base64-encodes a header value written with this prefix
    ENCODE_PREFIX: Final[str] = "rwEncodeBase64:"

    def __init__(self, sdk: RemnawaveSDK) -> None:
        self._client: AsyncClient = sdk._client  # type: ignore[assignment]

    async def _request(self, method: str, path: str, json: Optional[dict] = None) -> Any:
        response = await self._client.request(method, path, json=json)
        response.raise_for_status()
        return response.json()["response"]

    async def get_hosts(self) -> list[PanelHostDto]:
        hosts = await self._request("GET", "hosts")
        return [
            PanelHostDto(
                uuid=host["uuid"],
                remark=host.get("remark") or "",
                address=host.get("address") or "",
                port=int(host.get("port") or 0),
                sni=host.get("sni") or None,
                is_disabled=bool(host.get("isDisabled")),
                is_virtual=bool(host.get("xrayJsonTemplateUuid")),
                is_hidden=bool(host.get("isHidden")),
                inbound_uuid=(host.get("inbound") or {}).get("configProfileInboundUuid"),
            )
            for host in sorted(hosts, key=lambda h: h.get("viewPosition") or 0)
        ]

    async def get_squad_inbounds(self) -> dict[str, list[str]]:
        response = await self._request("GET", "internal-squads")
        return {
            squad["uuid"]: [inbound["uuid"] for inbound in squad.get("inbounds") or []]
            for squad in response.get("internalSquads") or []
        }

    async def set_host_disabled(self, uuid: str, disabled: bool) -> None:
        await self._request("PATCH", "hosts", {"uuid": uuid, "isDisabled": disabled})
        logger.info(f"Host '{uuid}' {'disabled' if disabled else 'enabled'} in the panel")

    async def get_announce(self) -> Optional[str]:
        settings = await self._request("GET", "subscription-settings")
        value = (settings.get("customResponseHeaders") or {}).get(self.ANNOUNCE_HEADER)
        if not value:
            return None
        return str(value).removeprefix(self.ENCODE_PREFIX)

    async def set_announce(self, text: str) -> None:
        settings = await self._request("GET", "subscription-settings")
        headers = dict(settings.get("customResponseHeaders") or {})
        headers[self.ANNOUNCE_HEADER] = f"{self.ENCODE_PREFIX}{text}"
        await self._request(
            "PATCH",
            "subscription-settings",
            {"uuid": settings["uuid"], "customResponseHeaders": headers},
        )
        logger.info("Subscription announce updated in the panel")


class GlobalpingProber(FleetProber):
    """TLS handshakes from probes inside Russian networks (Globalping) plus one made from
    this server.

    An open port proves nothing: the filtering equipment often lets the TCP handshake through
    and drops the data, so every check is a real TLS session with the host's SNI. The public
    Globalping API allows about 250 probe-tests an hour without a key; the budget per run
    keeps four runs an hour inside that, and a run never asks for more than is left (manual
    checks on top of the schedule used to run it dry, and every host showed 0/0).
    """

    API_BASE: Final[str] = "https://api.globalping.io/v1"
    PROBE_BUDGET: Final[int] = CHECK_PROBE_BUDGET
    PROBES_MIN: Final[int] = 3
    PROBES_MAX: Final[int] = 8
    DIRECT_TIMEOUT: Final[float] = 8.0
    POLL_ATTEMPTS: Final[int] = 10
    POLL_DELAY: Final[float] = 5.0

    def __init__(self, config: AppConfig) -> None:
        token = config.globalping_token
        self.headers = {"Authorization": f"Bearer {token.get_secret_value()}"} if token else {}

    def _client(self) -> AsyncClient:
        return AsyncClient(base_url=self.API_BASE, timeout=Timeout(20.0), headers=self.headers)

    async def quota(self) -> Optional[ProbeQuotaDto]:
        async with self._client() as client:
            return await self._quota(client)

    async def _quota(self, client: AsyncClient) -> Optional[ProbeQuotaDto]:
        try:
            response = await client.get("/limits")
            response.raise_for_status()
            create = response.json()["rateLimit"]["measurements"]["create"]
            return ProbeQuotaDto(
                remaining=int(create["remaining"]),
                reset_seconds=int(create["reset"]),
            )
        except (HTTPError, ValueError, KeyError, TypeError) as e:
            logger.warning(f"Globalping limits are not available: {e!r}")
            return None

    async def probe(self, targets: list[ProbeTargetDto]) -> dict[ProbeTargetDto, ProbeResultDto]:
        if not targets:
            return {}

        remote_task = asyncio.create_task(self._remote(targets))
        direct = await asyncio.gather(*(self._direct(target) for target in targets))
        remote = await remote_task

        results: dict[ProbeTargetDto, ProbeResultDto] = {}
        for target, direct_ok in zip(targets, direct):
            passed, total = remote.get(target, (0, 0))
            results[target] = ProbeResultDto(passed=passed, total=total, direct_ok=direct_ok)
        return results

    async def _direct(self, target: ProbeTargetDto) -> bool:
        context = ssl.create_default_context()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    target.address,
                    target.port,
                    ssl=context,
                    server_hostname=target.sni,
                ),
                timeout=self.DIRECT_TIMEOUT,
            )
        except (OSError, asyncio.TimeoutError, ssl.SSLError) as e:
            logger.debug(f"Direct TLS to '{target.address}:{target.port}' failed: {e!r}")
            return False

        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=2)
        except (OSError, asyncio.TimeoutError, ssl.SSLError):
            pass
        return True

    async def _remote(self, targets: list[ProbeTargetDto]) -> dict[ProbeTargetDto, tuple[int, int]]:
        limit = max(self.PROBES_MIN, min(self.PROBES_MAX, self.PROBE_BUDGET // len(targets)))
        try:
            async with self._client() as client:
                quota = await self._quota(client)
                if quota is not None:
                    affordable = quota.remaining // len(targets)
                    if affordable < self.PROBES_MIN:
                        logger.warning(
                            f"Globalping allows {quota.remaining} more probe-tests (refill in "
                            f"{quota.reset_seconds}s): remote probes skipped"
                        )
                        return {}
                    limit = min(limit, affordable)
                ids = await self._start(client, targets, limit)
                return await self._collect(client, ids)
        except (HTTPError, ValueError, KeyError) as e:
            # rate limit, outage of the service, malformed answer: the direct check remains
            logger.warning(f"Globalping measurement failed: {e!r}")
            return {}

    async def _start(
        self,
        client: AsyncClient,
        targets: list[ProbeTargetDto],
        limit: int,
    ) -> dict[ProbeTargetDto, str]:
        ids: dict[ProbeTargetDto, str] = {}
        # every target is measured from the probes of the first one, for comparable results
        locations: Any = [{"country": "RU"}]

        for target in targets:
            response = await client.post(
                "/measurements",
                json={
                    "type": "http",
                    "target": target.address,
                    "limit": limit,
                    "locations": locations,
                    "measurementOptions": {
                        "protocol": "HTTPS",
                        "port": target.port,
                        "request": {"method": "GET", "path": "/", "host": target.sni},
                    },
                },
            )
            if response.status_code == 429:
                logger.warning("Globalping rate limit reached, remaining targets not measured")
                break
            response.raise_for_status()
            ids[target] = response.json()["id"]
            if isinstance(locations, list):
                locations = ids[target]
            await asyncio.sleep(0.5)

        return ids

    async def _collect(
        self,
        client: AsyncClient,
        ids: dict[ProbeTargetDto, str],
    ) -> dict[ProbeTargetDto, tuple[int, int]]:
        results: dict[ProbeTargetDto, tuple[int, int]] = {}
        await asyncio.sleep(12)

        for _ in range(self.POLL_ATTEMPTS):
            for target, measurement_id in ids.items():
                if target in results:
                    continue
                response = await client.get(f"/measurements/{measurement_id}")
                response.raise_for_status()
                data = response.json()
                if data.get("status") != "finished":
                    continue
                probes = data.get("results") or []
                passed = sum(
                    1
                    for probe in probes
                    if probe["result"].get("status") == "finished"
                    and probe["result"].get("statusCode")
                )
                results[target] = (passed, len(probes))

            if len(results) == len(ids):
                break
            await asyncio.sleep(self.POLL_DELAY)

        return results
