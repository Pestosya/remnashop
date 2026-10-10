from typing import Optional

from adaptix import Retort
from loguru import logger
from redis.asyncio import Redis

from src.application.common import (
    EventPublisher,
    FleetProber,
    Interactor,
    PanelFleet,
    TranslatorHub,
    TranslatorRunner,
)
from src.application.common.dao import SettingsDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import FleetChangesDto, FleetSettingsDto, FleetStateDto, UserDto
from src.application.events import FleetStatusChangedEvent
from src.application.services.fleet import (
    ANNOUNCE_MAX_LENGTH,
    FleetEvaluationDto,
    evaluate,
    is_watched,
    server_names,
    target_of,
)
from src.application.use_cases.fleet.queries.servers import PANEL_SERVERS_KEY
from src.application.use_cases.fleet.queries.state import load_fleet_state, save_fleet_state
from src.core.config import AppConfig
from src.core.constants import PUBLIC_LANDING_PLANS_CACHE_KEY
from src.core.utils.time import datetime_now


class CheckFleet(Interactor[bool, Optional[FleetStateDto]]):
    """Probe every host users can see from Russian networks and act on the result.

    Always: remember the result and tell the admins when a server goes down or comes back
    (both only after two consecutive checks agree). Optionally, per settings: take dead
    hosts out of the subscriptions / put them back, and show an outage notice in the
    subscription announce. `force` runs the check even when the monitoring is switched off
    (the admin pressed the button).
    """

    required_permission = Permission.VIEW_FLEET

    def __init__(
        self,
        uow: UnitOfWork,
        config: AppConfig,
        settings_dao: SettingsDao,
        panel: PanelFleet,
        prober: FleetProber,
        redis: Redis,
        retort: Retort,
        translator_hub: TranslatorHub,
        event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.config = config
        self.settings_dao = settings_dao
        self.panel = panel
        self.prober = prober
        self.redis = redis
        self.retort = retort
        self.translator_hub = translator_hub
        self.event_publisher = event_publisher

    async def _execute(self, actor: UserDto, force: bool) -> Optional[FleetStateDto]:
        settings = await self.settings_dao.get()
        fleet = settings.extra.fleet

        if not fleet.enabled and not force:
            logger.debug("Fleet monitoring is disabled, skipping the check")
            return None

        hosts = await self.panel.get_hosts()
        hidden = set(fleet.hidden_hosts)
        targets = list(
            dict.fromkeys(
                target
                for host in hosts
                if is_watched(host, hidden) and (target := target_of(host)) is not None
            )
        )
        results = await self.prober.probe(targets)
        previous = await load_fleet_state(self.redis, self.retort)

        evaluation = evaluate(
            hosts=hosts,
            results=results,
            previous=previous,
            hidden_hosts=fleet.hidden_hosts,
            auto_hide=fleet.auto_hide,
            now=datetime_now(),
        )

        for uuid in evaluation.to_hide:
            await self.panel.set_host_disabled(uuid, True)
        for uuid in evaluation.to_restore:
            await self.panel.set_host_disabled(uuid, False)
        if evaluation.to_hide or evaluation.to_restore:
            # the purchase screens and the landing list the servers: show the change at once
            await self.redis.delete(PANEL_SERVERS_KEY, PUBLIC_LANDING_PLANS_CACHE_KEY)

        i18n = self.translator_hub.get_translator_by_locale(self.config.default_locale)
        await self._sync_announce(fleet, evaluation, i18n)

        if fleet.hidden_hosts != evaluation.hidden_hosts:
            fleet.hidden_hosts = evaluation.hidden_hosts

        if settings.changed_data:
            async with self.uow:
                await self.settings_dao.update(settings)
                await self.uow.commit()

        await save_fleet_state(self.redis, self.retort, evaluation.state)

        if not evaluation.changes.is_empty:
            logger.info(f"Fleet changes: {evaluation.changes}")
            await self.event_publisher.publish(
                FleetStatusChangedEvent(
                    report=self._report(evaluation.changes, i18n),
                    all_down=evaluation.changes.all_down,
                )
            )

        return evaluation.state

    async def _sync_announce(
        self,
        fleet: FleetSettingsDto,
        evaluation: FleetEvaluationDto,
        i18n: TranslatorRunner,
    ) -> None:
        """Show an outage notice while servers are down and put the admin's own announce back
        afterwards. An announce the admin edits in the meantime becomes the one to restore."""
        down, working = server_names(evaluation.state)

        if not fleet.announce or not down:
            if fleet.outage_announce is None:
                return
            # the outage is over (or the option was switched off): restore
            current = await self.panel.get_announce()
            if current == fleet.outage_announce and fleet.base_announce is not None:
                await self.panel.set_announce(fleet.base_announce)
            fleet.base_announce = None
            fleet.outage_announce = None
            return

        desired = self._outage_text(down, working, i18n)
        current = await self.panel.get_announce()
        if current == desired:
            return
        if current != fleet.outage_announce:
            fleet.base_announce = current or ""
        await self.panel.set_announce(desired)
        fleet.outage_announce = desired

    def _outage_text(self, down: list[str], working: list[str], i18n: TranslatorRunner) -> str:
        support = self.config.bot.support_username.get_secret_value()
        short = i18n.get("fleet-announce.outage-short", down=", ".join(down), support=support)
        if not working:
            return short[:ANNOUNCE_MAX_LENGTH]

        text = i18n.get(
            "fleet-announce.outage",
            down=", ".join(down),
            working=", ".join(working),
            support=support,
        )
        # the panel limits the announce: drop the list of working servers first
        return text if len(text) <= ANNOUNCE_MAX_LENGTH else short[:ANNOUNCE_MAX_LENGTH]

    @staticmethod
    def _report(changes: FleetChangesDto, i18n: TranslatorRunner) -> str:
        lines: list[str] = []
        for key, names in (
            ("down", changes.down),
            ("recovered", changes.recovered),
            ("hidden", changes.hidden),
            ("restored", changes.restored),
        ):
            lines += [i18n.get(f"event-fleet.line-{key}", name=name) for name in names]
        if changes.all_down:
            lines.append(i18n.get("event-fleet.line-all-down"))
        return "\n".join(lines)
