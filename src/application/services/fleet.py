"""Decisions of the reachability automation. Pure functions: no I/O."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Final, Iterable, Optional

from src.application.dto import (
    FleetChangesDto,
    FleetHostStateDto,
    FleetStateDto,
    PanelHostDto,
    ProbeResultDto,
    ProbeTargetDto,
)
from src.core.enums import FleetStatus

# share of remote probes that completed a TLS handshake
OK_FROM = 0.7
DOWN_BELOW = 0.2
# with fewer remote answers than this the remote result says nothing
MIN_REMOTE_PROBES = 3
# consecutive checks before a host counts as down / as back
CONFIRM_DOWN = 2
CONFIRM_UP = 2

ANNOUNCE_MAX_LENGTH = 200

# `{servers}` in a plan's description is replaced with the plan's servers
SERVERS_PLACEHOLDER: Final[str] = "{servers}"
# UTF-16 units a description may take on a purchase screen, and the least the list gets
DESCRIPTION_BUDGET: Final[int] = 480
SERVERS_MIN_BUDGET: Final[int] = 100

_ALIVE = (FleetStatus.OK, FleetStatus.PARTIAL)


@dataclass(kw_only=True)
class FleetEvaluationDto:
    state: FleetStateDto
    changes: FleetChangesDto = field(default_factory=FleetChangesDto)
    to_hide: list[str] = field(default_factory=list)  # host uuids
    to_restore: list[str] = field(default_factory=list)
    hidden_hosts: list[str] = field(default_factory=list)  # the new durable list


def target_of(host: PanelHostDto) -> Optional[ProbeTargetDto]:
    if host.is_virtual or not host.sni or not host.address or not host.port:
        return None
    return ProbeTargetDto(address=host.address, port=host.port, sni=host.sni)


def is_watched(host: PanelHostDto, hidden_hosts: set[str]) -> bool:
    """Hosts users can see, plus the ones the automation has hidden itself."""
    if target_of(host) is None:
        return False
    return not host.is_disabled or host.uuid in hidden_hosts


def classify(result: Optional[ProbeResultDto], network_ok: bool) -> FleetStatus:
    if result is None:
        return FleetStatus.UNKNOWN

    if result.total >= MIN_REMOTE_PROBES:
        share = result.passed / result.total
        if share >= OK_FROM:
            return FleetStatus.OK
        if share >= DOWN_BELOW:
            return FleetStatus.PARTIAL
        return FleetStatus.DOWN

    # No usable remote result: fall back to the handshake made from this server, but only
    # when this server's own network demonstrably works.
    if result.direct_ok is None or not network_ok:
        return FleetStatus.UNKNOWN
    return FleetStatus.OK if result.direct_ok else FleetStatus.DOWN


def _advance(
    host: PanelHostDto,
    result: Optional[ProbeResultDto],
    prev: Optional[FleetHostStateDto],
    network_ok: bool,
    changes: FleetChangesDto,
) -> FleetHostStateDto:
    """The host's new state: status, streaks, and whether the admins must be told."""
    status = classify(result, network_ok)
    bad = prev.bad_streak if prev else 0
    good = prev.good_streak if prev else 0
    alerted = prev.alerted if prev else False

    if status == FleetStatus.DOWN:
        bad, good = bad + 1, 0
    elif status in _ALIVE:
        bad, good = 0, good + 1

    if status == FleetStatus.DOWN and bad >= CONFIRM_DOWN and not alerted:
        alerted = True
        changes.down.append(host.remark)
    elif alerted and status in _ALIVE and good >= CONFIRM_UP:
        alerted = False
        changes.recovered.append(host.remark)

    return FleetHostStateDto(
        uuid=host.uuid,
        remark=host.remark,
        address=host.address,
        port=host.port,
        status=status,
        passed=result.passed if result else 0,
        total=result.total if result else 0,
        direct_ok=result.direct_ok if result else None,
        bad_streak=bad,
        good_streak=good,
        alerted=alerted,
    )


def _hide_and_restore(
    states: list[FleetHostStateDto],
    hidden: set[str],
    can_hide: bool,
    evaluation: FleetEvaluationDto,
) -> None:
    """A host the automation hid is put back once it recovers, even if hiding has been
    switched off since: otherwise it would stay hidden forever."""
    changes = evaluation.changes

    for state in states:
        if state.hidden:
            if state.status in _ALIVE and state.good_streak >= CONFIRM_UP:
                state.hidden = False
                hidden.discard(state.uuid)
                evaluation.to_restore.append(state.uuid)
                changes.restored.append(state.remark)
        elif can_hide and state.status == FleetStatus.DOWN and state.alerted:
            state.hidden = True
            hidden.add(state.uuid)
            evaluation.to_hide.append(state.uuid)
            changes.hidden.append(state.remark)


def evaluate(
    hosts: list[PanelHostDto],
    results: dict[ProbeTargetDto, ProbeResultDto],
    previous: FleetStateDto,
    hidden_hosts: list[str],
    auto_hide: bool,
    now: datetime,
) -> FleetEvaluationDto:
    known = {host.uuid: host for host in hosts}
    # forget hosts that were deleted or that the admin switched back on by hand
    hidden = {uuid for uuid in hidden_hosts if uuid in known and known[uuid].is_disabled}
    network_ok = any(r.direct_ok or r.passed for r in results.values())
    changes = FleetChangesDto()
    states: list[FleetHostStateDto] = []

    for host in hosts:
        if not is_watched(host, hidden):
            continue
        target = target_of(host)
        state = _advance(
            host=host,
            result=results.get(target) if target else None,
            prev=previous.get(host.uuid),
            network_ok=network_ok,
            changes=changes,
        )
        state.hidden = host.uuid in hidden
        states.append(state)

    has_alive = any(s.status in _ALIVE and not s.hidden for s in states)
    changes.all_down = bool(changes.down) and not has_alive

    evaluation = FleetEvaluationDto(
        state=FleetStateDto(checked_at=now, hosts=states),
        changes=changes,
    )
    # hiding is pointless (and leaves an empty subscription) when nothing else works
    _hide_and_restore(states, hidden, can_hide=auto_hide and has_alive, evaluation=evaluation)

    evaluation.hidden_hosts = sorted(hidden)
    return evaluation


def short_name(remark: str) -> str:
    """'🇦🇹 Австрия 🇦🇹' -> '🇦🇹 Австрия': drop the decorative tail."""
    tokens = remark.split()
    while len(tokens) > 1 and not any(ch.isalnum() for ch in tokens[-1]):
        tokens.pop()
    return " ".join(tokens)


def server_names(state: FleetStateDto) -> tuple[list[str], list[str]]:
    """(down, working) server names for the announce. Hosts are grouped by address: a server
    is down only when every host on it is confirmed down, and it is named after its
    shortest remark (the plain one, without the protocol decorations)."""
    groups: dict[str, list[FleetHostStateDto]] = {}
    for host in state.hosts:
        groups.setdefault(host.address, []).append(host)

    down: list[str] = []
    working: list[str] = []
    for hosts in groups.values():
        name = short_name(min((h.remark for h in hosts), key=len))
        if all(h.alerted and h.status == FleetStatus.DOWN for h in hosts):
            down.append(name)
        elif any(h.status in _ALIVE and not h.hidden for h in hosts):
            working.append(name)
    return down, working


def server_statuses(state: FleetStateDto) -> list[tuple[str, FleetStatus]]:
    """One line per server for the users' help menu: the server's name and the best status
    among its hosts (a server whose plain entry is cut may still work through another one).
    Servers the check knows nothing about are left out."""
    groups: dict[str, list[FleetHostStateDto]] = {}
    for host in state.hosts:
        groups.setdefault(host.address, []).append(host)

    rank = {FleetStatus.OK: 0, FleetStatus.PARTIAL: 1, FleetStatus.DOWN: 2}
    servers: list[tuple[str, FleetStatus]] = []
    for hosts in groups.values():
        known = [h.status for h in hosts if h.status in rank]
        if not known:
            continue
        name = short_name(min((h.remark for h in hosts), key=len))
        servers.append((name, min(known, key=lambda status: rank[status])))
    return servers


def servers_for_squads(
    hosts: list[PanelHostDto],
    squad_inbounds: dict[str, list[str]],
    squads: Iterable[str],
) -> list[str]:
    """Names of the hosts a subscription with these squads gets, in the panel's order: the
    enabled, visible hosts whose inbound belongs to one of the squads."""
    inbounds = {inbound for squad in squads for inbound in squad_inbounds.get(squad, [])}
    names = [
        short_name(host.remark)
        for host in hosts
        if not host.is_disabled and not host.is_hidden and host.inbound_uuid in inbounds
    ]
    return list(dict.fromkeys(names))


def utf16_len(text: str) -> int:
    """Length the way Telegram counts it."""
    return len(text.encode("utf-16-le")) // 2


def describe_plan(
    description: Optional[str],
    servers: list[str],
    more: Callable[[int], str],
    budget: int = DESCRIPTION_BUDGET,
) -> Optional[str]:
    """A plan's description with its servers in it, so the list follows the panel instead of
    being typed by hand.

    `{servers}` in the typed text marks where the list goes; without the marker the list is
    appended after the text, and an empty description is the list alone. The list is cut to
    fit what the text leaves of `budget` (UTF-16 units): the purchase screens are banner
    captions, which Telegram limits. `more(n)` words the "and n more" line.
    """
    text = (description or "").strip()
    typed = text.replace(SERVERS_PLACEHOLDER, "")
    room = max(SERVERS_MIN_BUDGET, budget - utf16_len(typed))

    lines: list[str] = []
    used = 0
    for index, name in enumerate(servers):
        rest = len(servers) - index - 1
        reserve = utf16_len(more(rest)) + 1 if rest else 0
        if used + utf16_len(name) + 1 + reserve > room:
            lines.append(more(rest + 1))
            break
        lines.append(name)
        used += utf16_len(name) + 1
    listed = "\n".join(lines)

    if SERVERS_PLACEHOLDER in text:
        text = text.replace(SERVERS_PLACEHOLDER, listed).strip()
    elif listed:
        text = f"{text}\n\n{listed}" if text else listed

    return text or None
