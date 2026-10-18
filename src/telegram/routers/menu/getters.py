from typing import Any
from urllib.parse import quote

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from src.application.common import BotService, Remnawave, TranslatorRunner
from src.application.common.dao import ReferralDao, SettingsDao, SubscriptionDao
from src.application.dto import TelegramUserDto
from src.application.services.fleet import (
    STATE_STALE_AFTER,
    server_statuses,
    state_age,
    utf16_len,
)
from src.application.use_cases.fleet.queries.state import GetFleetState
from src.application.use_cases.misc.queries.menu import GetMenuData
from src.application.use_cases.points.exchange import GetPointsExchange
from src.application.use_cases.subscription.commands.purchase import expires_after
from src.core.config import AppConfig
from src.core.constants import (
    POINTS_DAYS_KEY,
    POINTS_FROM_PAYMENT_KEY,
    POINTS_PLAN_KEY,
    T_ME,
    TEXT_MEDIA_MAX_LENGTH,
)
from src.core.exceptions import MenuRenderError
from src.core.utils.i18n_helpers import (
    i18n_format_bytes_to_unit,
    i18n_format_date,
    i18n_format_days,
    i18n_format_device_limit,
    i18n_format_expire_time,
    i18n_format_traffic_limit,
    i18n_format_until,
)
from src.core.utils.i18n_keys import ByteUnitKey
from src.core.utils.time import datetime_now, get_traffic_reset_delta


@inject
async def menu_getter(
    dialog_manager: DialogManager,
    config: AppConfig,
    user: TelegramUserDto,
    bot_service: FromDishka[BotService],
    i18n: FromDishka[TranslatorRunner],
    get_menu_data: FromDishka[GetMenuData],
    settings_dao: FromDishka[SettingsDao],
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        menu_data = await get_menu_data(user)
        settings = await settings_dao.get()
        support_url = bot_service.get_support_url(text=i18n.get("message.help"))

        purchase_discount = user.purchase_discount or 0
        personal_discount = user.personal_discount or 0
        show_purchase_discount = purchase_discount > 0 and purchase_discount >= personal_discount
        show_personal_discount = personal_discount > 0 and not show_purchase_discount

        data: dict[str, Any] = {
            # user
            "telegram_id": user.telegram_id,
            "email": user.email,
            "name": user.name,
            "personal_discount": personal_discount,
            "show_personal_discount": show_personal_discount,
            "purchase_discount": purchase_discount,
            "show_purchase_discount": show_purchase_discount,
            # ui / config
            "is_mini_app": config.bot.is_mini_app,
            "is_mini_app_reserve": config.bot.is_mini_app and settings.extra.mini_app_reserve,
            "support_url": support_url,
            "web_enabled": config.web_enabled,
            "web_cabinet_url": config.web_cabinet_url.strip(),
            # referral
            "referral_enabled": menu_data.is_referral_enabled,
            # defaults
            "has_subscription": False,
            "connectable": False,
            "trial_available": False,
            "trial_is_free": True,
            "trial_price": "",
            "has_device_limit": False,
            "is_trial": False,
            # subscription-related (nullable)
            "status": None,
            "subscription_type": None,
            "traffic_limit": None,
            "device_limit": None,
            "expire_time": None,
            "reset_time": None,
            "connection_url": None,
            "subscription_url": None,
            "row_1_buttons": [b for b in menu_data.custom_buttons if b.index in (1, 2)],
            "row_2_buttons": [b for b in menu_data.custom_buttons if b.index in (3, 4)],
            "row_3_buttons": [b for b in menu_data.custom_buttons if b.index in (5, 6)],
        }

        if not menu_data.current_subscription:
            logger.debug(f"{user.log} has no active subscription")
            trial_plan = menu_data.available_trial
            trial_is_free = True
            trial_price_str = ""
            if trial_plan and menu_data.is_trial_available:
                currency = settings.default_currency
                raw_price = trial_plan.durations[0].get_price(currency)
                trial_is_free = raw_price == 0
                trial_price_str = (
                    f"{raw_price.normalize():f} {currency.symbol}" if not trial_is_free else ""
                )
            data["trial_available"] = menu_data.is_trial_available and menu_data.available_trial
            data["trial_is_free"] = trial_is_free
            data["trial_price"] = trial_price_str
            return data

        subscription = menu_data.current_subscription
        usage = menu_data.usage

        data.update(
            {
                "plan_name": i18n.get(subscription.plan_snapshot.name),
                "is_endless": int(subscription.is_unlimited),
                "expire_date": i18n_format_date(subscription.expire_at),
                # what is in use, when the panel told us in time
                "devices_known": int(usage is not None),
                "devices_used": usage.devices if usage else 0,
                "device_max": subscription.device_limit,
                "traffic_known": int(usage is not None),
                "traffic_used": i18n_format_bytes_to_unit(
                    usage.traffic_used_bytes if usage else 0, min_unit=ByteUnitKey.MEGABYTE
                ),
                "traffic_unlimited": int(subscription.traffic_limit == 0),
                "has_subscription": True,
                "is_trial": subscription.is_trial,
                "traffic_strategy": subscription.traffic_limit_strategy,
                "status": subscription.current_status,
                "subscription_type": subscription.limit_type,
                "traffic_limit": i18n_format_traffic_limit(subscription.traffic_limit),
                "device_limit": i18n_format_device_limit(subscription.device_limit),
                "expire_time": i18n_format_expire_time(subscription.expire_at),
                "reset_time": i18n_format_expire_time(
                    get_traffic_reset_delta(
                        subscription.traffic_limit_strategy,
                        subscription.created_at,
                    )
                ),
                "connectable": subscription.is_active,
                "has_device_limit": (
                    subscription.has_devices_limit or subscription.device_limit == 0
                )
                if subscription.is_active
                else False,
                "connection_url": config.bot.mini_app_url
                if isinstance(config.bot.mini_app_url, str)
                else subscription.url,
                "subscription_url": subscription.url,
            }
        )
        logger.debug(f"Menu data for user {user.log}: {data}")
        return data

    except Exception as e:
        raise MenuRenderError(str(e)) from e


def get_platform_icon(i18n: TranslatorRunner, platform: str | None) -> str:
    known_platforms = {"ios", "android", "windows", "macos", "linux"}

    if platform and platform.lower() in known_platforms:
        return i18n.get(f"platform-icon.{platform.lower()}")
    return i18n.get("platform-icon.default")


@inject
async def devices_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    i18n: FromDishka[TranslatorRunner],
    subscription_dao: FromDishka[SubscriptionDao],
    remnawave: FromDishka[Remnawave],
    settings_dao: FromDishka[SettingsDao],
    **kwargs: Any,
) -> dict[str, Any]:
    current_subscription = await subscription_dao.get_current(user.id)

    if not current_subscription:
        raise ValueError(f"Current subscription for user '{user.telegram_id}' not found")

    devices = await remnawave.get_devices(current_subscription.remna_id)

    formatted_devices = [
        {
            "index": index,
            "hwid": device.hwid,
            "platform": device.platform or False,
            "device_model": device.device_model or False,
            "user_agent": device.user_agent,
            "platform_icon": get_platform_icon(i18n, device.platform),
            "created_at": device.created_at.strftime("%d.%m.%Y"),
            "label": i18n.get(
                "btn-devices.item",
                platform_icon=get_platform_icon(i18n, device.platform),
                platform=device.platform or False,
                device_model=device.device_model or False,
                created_at=device.created_at.strftime("%d.%m.%Y"),
            ),
        }
        for index, device in enumerate(devices)
    ]

    dialog_manager.dialog_data["hwid_map"] = formatted_devices

    settings = await settings_dao.get()

    return {
        "current_count": len(devices),
        "max_count": current_subscription.device_limit,
        "devices": formatted_devices,
        "devices_empty": len(devices) == 0,
        "has_devices": len(devices) > 0,
        "device_single_enabled": int(settings.extra.device_single_reset.enabled),
        "device_all_enabled": int(settings.extra.device_all_reset.enabled),
        "link_reset_enabled": int(settings.extra.link_reset.enabled),
    }


@inject
async def device_confirm_delete_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "device_model": dialog_manager.dialog_data.get("selected_device_model", ""),
        "platform": dialog_manager.dialog_data.get("selected_platform", ""),
        "platform_icon": dialog_manager.dialog_data.get("selected_platform_icon", ""),
        "created_at": dialog_manager.dialog_data.get("selected_created_at", ""),
    }


@inject
async def invite_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    bot_service: FromDishka[BotService],
    i18n: FromDishka[TranslatorRunner],
    settings_dao: FromDishka[SettingsDao],
    referral_dao: FromDishka[ReferralDao],
    **kwargs: Any,
) -> dict[str, Any]:
    settings = await settings_dao.get()
    referrals = await referral_dao.get_referrals_count(user.id)
    payments = await referral_dao.get_referrals_with_payment_count(user.id)
    referral_url = await bot_service.get_referral_url(user.referral_code)
    support_url = bot_service.get_support_url(text=i18n.get("message.withdraw-points"))

    return {
        "reward_type": settings.referral.reward.type,
        "referrals": referrals,
        "payments": payments,
        "points": user.points,
        "is_points_reward": settings.referral.reward.is_points,
        "has_points": True if user.points > 0 else False,
        "exchange_enabled": settings.extra.points.exchange_enabled,
        "referral_url": referral_url,
        # Telegram's own "share": the chat picker with a ready message that holds the link, so
        # whatever the user taps, the friend gets the referral link (not a bare inline query)
        "share_url": f"{T_ME}share/url?url={quote(referral_url, safe='')}"
        f"&text={quote(i18n.get('inline-invite.share'), safe='')}",
        "withdraw": support_url,
        "referral_reset_enabled": int(settings.extra.referral_reset.enabled),
    }


@inject
async def invite_about_getter(
    dialog_manager: DialogManager,
    i18n: FromDishka[TranslatorRunner],
    settings_dao: FromDishka[SettingsDao],
    **kwargs: Any,
) -> dict[str, Any]:
    settings = await settings_dao.get()
    reward_config = settings.referral.reward.config

    max_level = settings.referral.level.value
    identical_reward = settings.referral.reward.is_identical

    reward_levels: dict[str, str] = {}
    for lvl, val in reward_config.items():
        if lvl.value <= max_level:
            reward_levels[f"reward_level_{lvl.value}"] = i18n.get(
                "msg-invite-reward",
                value=val,
                reward_strategy_type=settings.referral.reward.strategy,
                reward_type=settings.referral.reward.type,
            )

    return {
        **reward_levels,
        "reward_type": settings.referral.reward.type,
        "reward_strategy_type": settings.referral.reward.strategy,
        "accrual_strategy": settings.referral.accrual_strategy,
        "identical_reward": identical_reward,
        "max_level": max_level,
    }


@inject
async def help_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    bot_service: FromDishka[BotService],
    i18n: FromDishka[TranslatorRunner],
    get_fleet_state: FromDishka[GetFleetState],
    **kwargs: Any,
) -> dict[str, Any]:
    """Troubleshooting menu: what to try, and what the last reachability check says and when.
    Statuses from a check that has stopped are not shown: they may say the opposite of now."""
    support_url = bot_service.get_support_url(text=i18n.get("message.help"))
    state = await get_fleet_state(user)
    age = state_age(state, datetime_now())
    if age is not None and age > STATE_STALE_AFTER:
        return {"servers": i18n.get("msg-menu-help.stale") + "\n\n", "support_url": support_url}

    minutes = int(age.total_seconds() // 60) if age else 0
    statuses = server_statuses(state)
    lines = [
        i18n.get("msg-menu-help.server", name=name, status=status) for name, status in statuses
    ]

    # the screen is a banner caption: what does not fit is said shorter, then cut
    # room for the list: the caption without it, the heading, and an "and n more" line
    budget = (
        TEXT_MEDIA_MAX_LENGTH
        - utf16_len(i18n.get("msg-menu-help.main", servers=""))
        - utf16_len(i18n.get("msg-menu-help.servers", servers="", minutes=minutes))
        - utf16_len(i18n.get("msg-menu-help.more", count=len(statuses)))
        - 4
    )
    if utf16_len("\n".join(lines)) > budget:
        lines = [
            i18n.get("msg-menu-help.server-short", name=name, status=status)
            for name, status in statuses
        ]
        legend = i18n.get("msg-menu-help.legend")
        budget -= utf16_len(legend) + 1
        while lines and utf16_len("\n".join(lines)) > budget:
            lines.pop()
        if len(lines) < len(statuses):
            lines.append(i18n.get("msg-menu-help.more", count=len(statuses) - len(lines)))
        lines.append(legend)

    servers = (
        i18n.get("msg-menu-help.servers", servers="\n".join(lines), minutes=minutes) + "\n\n"
        if lines
        else ""
    )

    return {"servers": servers, "support_url": support_url}


@inject
async def points_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    i18n: FromDishka[TranslatorRunner],
    settings_dao: FromDishka[SettingsDao],
    get_points_exchange: FromDishka[GetPointsExchange],
    **kwargs: Any,
) -> dict[str, Any]:
    """Exchange of points for a subscription: the balance and what it can buy."""
    settings = await settings_dao.get()
    exchange = await get_points_exchange(user, dialog_manager.dialog_data.get(POINTS_PLAN_KEY))

    offers = []
    for offer in exchange.offers:
        key, kw = i18n_format_days(offer.days)
        offers.append(
            {
                "days": offer.days,
                "period": i18n.get(key, **kw),
                "cost": offer.cost,
                "affordable": int(offer.affordable),
            }
        )

    return {
        "points": exchange.points,
        "rate": settings.extra.points.points_per_ruble,
        "status": exchange.status,
        "purchase_type": exchange.purchase_type,
        "plan": i18n.get(exchange.plan.name) if exchange.plan else "",
        "plans": [{"id": plan.id, "name": i18n.get(plan.name)} for plan in exchange.plans],
        "offers": offers,
        # a plan the user picked themselves can be picked again
        "plan_chosen": POINTS_PLAN_KEY in dialog_manager.dialog_data,
    }


@inject
async def points_confirm_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    i18n: FromDishka[TranslatorRunner],
    get_points_exchange: FromDishka[GetPointsExchange],
    subscription_dao: FromDishka[SubscriptionDao],
    **kwargs: Any,
) -> dict[str, Any]:
    exchange = await get_points_exchange(user, dialog_manager.dialog_data.get(POINTS_PLAN_KEY))
    offer = exchange.get_offer(dialog_manager.dialog_data.get(POINTS_DAYS_KEY, 0))

    if offer is None or exchange.plan is None:
        # the plan or its durations changed under the user: nothing to confirm any more
        return {
            "available": 0,
            "purchase_type": exchange.purchase_type,
            "plan": "",
            "period": "",
            "cost": 0,
            "points": exchange.points,
            "remaining": exchange.points,
            "new_expire": 0,
            "from_payment": bool(dialog_manager.dialog_data.get(POINTS_FROM_PAYMENT_KEY)),
        }

    key, kw = i18n_format_days(offer.days)
    current = await subscription_dao.get_current(user.id)
    return {
        "available": int(offer.affordable),
        "purchase_type": exchange.purchase_type,
        "plan": i18n.get(exchange.plan.name),
        "period": i18n.get(key, **kw),
        "cost": offer.cost,
        "points": exchange.points,
        "remaining": exchange.points - offer.cost,
        "new_expire": i18n_format_until(expires_after(exchange.purchase_type, current, offer.days)),
        "from_payment": bool(dialog_manager.dialog_data.get(POINTS_FROM_PAYMENT_KEY)),
    }
