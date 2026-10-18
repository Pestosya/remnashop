import asyncio
from dataclasses import fields, is_dataclass
from datetime import timedelta
from typing import Optional, Union

from loguru import logger
from packaging.version import Version
from remnapy import RemnawaveSDK
from remnapy.exceptions import ApiError, AuthenticationError, ConflictError, NotFoundError
from remnapy.models import (
    CreateUserRequestDto,
    DeleteUserAllHwidDeviceRequestDto,
    DeleteUserHwidDeviceRequestDto,
    DropByUserIds,
    DropConnectionsRequestDto,
    GetMetadataResponseDto,
    TargetAllNodes,
    UpdateUserRequestDto,
    UserResponseDto,
)
from remnapy.models.hwid import HwidDeviceDto

from src.application.common import Remnawave
from src.application.common.remnawave import T
from src.application.dto import (
    PlanSnapshotDto,
    RemnaSubscriptionDto,
    SquadInfoDto,
    SubscriptionDto,
    UserDto,
)
from src.core.constants import REMNAWAVE_MIN_VERSION, USERS_STREAM_PAGE_SIZE
from src.core.enums import SubscriptionStatus
from src.core.utils.converters import days_to_datetime, gb_to_bytes
from src.core.utils.time import datetime_now


class RemnawaveImpl(Remnawave):
    def __init__(self, sdk: RemnawaveSDK) -> None:
        self.sdk = sdk

    async def try_connection(self) -> Version:
        for attempt in range(1, 4):
            try:
                metadata = await self.sdk.system.get_metadata()
                break
            except AuthenticationError as e:
                logger.error(f"Authentication failed when connecting to Remnawave panel: '{e}'")
                raise
            except Exception as e:
                if attempt < 3:
                    logger.warning(
                        f"Failed to connect to Remnawave panel (attempt {attempt}/3): '{e}', "
                        f"retrying in 5s..."
                    )
                    await asyncio.sleep(5)
                else:
                    logger.error(f"Failed to connect to Remnawave panel after 3 attempts: '{e}'")
                    raise

        if not isinstance(metadata, GetMetadataResponseDto):
            logger.error(f"Invalid response from Remnawave panel: '{metadata}'")
            raise ValueError(f"Invalid response from Remnawave panel: {metadata}")

        panel_version = Version(metadata.version)
        if panel_version < REMNAWAVE_MIN_VERSION:
            logger.error(
                f"Remnawave panel version '{panel_version}' is not compatible. "
                f"Minimum required version: '{REMNAWAVE_MIN_VERSION}'"
            )
            raise ValueError(
                f"Remnawave panel version '{panel_version}' is not compatible. "
                f"Minimum required version: '{REMNAWAVE_MIN_VERSION}'"
            )

        logger.info(f"Successfully connected to Remnawave panel (version: {panel_version})")
        return panel_version

    async def create_user(
        self,
        user: UserDto,
        plan: Optional[PlanSnapshotDto] = None,
        subscription: Optional[SubscriptionDto] = None,
    ) -> UserResponseDto:
        request_dto = self._build_create_request(user, plan, subscription)

        try:
            remna_user = await self.sdk.users.create_user(request_dto)
            logger.info(
                f"RemnaUser '{remna_user.username}' created successfully. "
                f"ID: '{remna_user.id}', telegram_id: '{remna_user.telegram_id}'"
            )
            return remna_user
        except ConflictError:
            logger.warning(f"RemnaUser '{request_dto.username}' already exists in panel")
            raise

    async def update_user(
        self,
        user: UserDto,
        remna_id: int,
        plan: Optional[PlanSnapshotDto] = None,
        subscription: Optional[SubscriptionDto] = None,
        reset_traffic: bool = False,
    ) -> UserResponseDto:
        request_dto = self._build_update_request(user, remna_id, plan, subscription)

        try:
            remna_user = await self.sdk.users.update_user(request_dto)
            logger.info(
                f"RemnaUser '{remna_user.username}' updated successfully. "
                f"ID: '{remna_user.id}', telegram_id: '{remna_user.telegram_id}'"
            )
        except NotFoundError:
            logger.warning(f"RemnaUser with ID '{request_dto.id}' not found")
            raise
        except ApiError as e:
            # `str(ApiError)` only carries the generic message ("Validation
            # failed"); the per-field detail lives in `errors`.
            logger.error(
                f"Panel rejected update for RemnaUser '{request_dto.id}': "
                f"{e.error.message} (code {e.error.code}), details: {e.error.errors}, "
                f"sent: {request_dto.model_dump(by_alias=True, exclude_none=True)}"
            )
            raise

        if reset_traffic:
            await self.reset_traffic(remna_id)

        return remna_user

    async def enable_user(self, remna_id: int) -> None:
        try:
            await self.sdk.users.enable_user(remna_id)
            logger.info(f"RemnaUser '{remna_id}' enabled successfully")
        except NotFoundError:
            logger.debug(f"RemnaUser '{remna_id}' not found in panel")
            raise

    async def disable_user(self, remna_id: int) -> None:
        try:
            await self.sdk.users.disable_user(remna_id)
            logger.info(f"RemnaUser '{remna_id}' disabled successfully")
        except NotFoundError:
            logger.debug(f"RemnaUser '{remna_id}' not found in panel")
            raise

    async def delete_user(self, remna_id: int) -> bool:
        try:
            await self.sdk.users.delete_user(remna_id)
        except NotFoundError:
            logger.debug(f"RemnaUser '{remna_id}' not found in panel")
            return False

        logger.info(f"RemnaUser '{remna_id}' deleted successfully")
        return True

    async def get_user_by_id(self, remna_id: int) -> Optional[UserResponseDto]:
        try:
            remna_user = await self.sdk.users.get_user_by_id(remna_id)
            logger.info(f"Fetched RemnaUser '{remna_id}' from panel")
            return remna_user
        except NotFoundError:
            logger.debug(f"RemnaUser '{remna_id}' not found in panel")
            return None

    async def get_user_by_username(self, username: str) -> Optional[UserResponseDto]:
        try:
            remna_user = await self.sdk.users.get_user_by_username(username)
            logger.debug(f"Fetched RemnaUser '{username}' from panel")
            return remna_user
        except NotFoundError:
            logger.debug(f"RemnaUser '{username}' not found in panel")
            return None

    async def get_user_by_short_uuid(self, short_uuid: str) -> Optional[UserResponseDto]:
        try:
            remna_user = await self.sdk.users.get_user_by_short_uuid(short_uuid)
            logger.debug(f"Fetched RemnaUser by short UUID '{short_uuid}' from panel")
            return remna_user
        except NotFoundError:
            logger.debug(f"RemnaUser with short UUID '{short_uuid}' not found in panel")
            return None

    async def get_users_by_telegram_id(self, telegram_id: int) -> list[UserResponseDto]:
        users = await self._stream_users(telegram_id=str(telegram_id))
        logger.debug(f"Fetched {len(users)} RemnaUsers for telegram_id '{telegram_id}'")
        return users

    async def get_all_users(self, limit: int, offset: int) -> list[UserResponseDto]:
        response = await self.sdk.users.get_all_users(start=offset, size=limit)
        logger.debug(f"Fetched {len(response.users)} RemnaUsers (limit={limit}, offset={offset})")
        return response.users

    async def get_users_by_email(self, email: str) -> list[UserResponseDto]:
        users = await self._stream_users(email=email)
        logger.debug(f"Fetched {len(users)} RemnaUsers for email '{email}'")
        return users

    async def _stream_users(
        self,
        telegram_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> list[UserResponseDto]:
        """Collect every page of `GET /users/stream` for a single filter.

        Panel 3.x dropped the dedicated `by-telegram-id` / `by-email`
        endpoints; the cursor-paginated stream is the replacement.
        """
        users: list[UserResponseDto] = []
        cursor: Optional[int] = None

        while True:
            response = await self.sdk.users.get_users_stream(
                size=USERS_STREAM_PAGE_SIZE,
                cursor=cursor,
                telegram_id=telegram_id,
                email=email,
            )
            users.extend(response.users)

            if not response.has_more or not response.next_cursor:
                break

            try:
                cursor = int(response.next_cursor)
            except ValueError:
                logger.warning(f"Unexpected users stream cursor '{response.next_cursor}'")
                break

        return users

    async def get_devices(self, remna_id: int) -> list[HwidDeviceDto]:
        response = await self.sdk.hwid.get_hwid_user(remna_id)
        logger.debug(f"Fetched {response.total} devices for RemnaUser '{remna_id}'")
        return response.devices if response.total else []

    async def delete_device(self, remna_id: int, hwid_uuid: str) -> Optional[int]:
        try:
            response = await self.sdk.hwid.delete_hwid_to_user(
                DeleteUserHwidDeviceRequestDto(user_id=remna_id, hwid=hwid_uuid)
            )
            logger.info(
                f"Deleted HWID device '{hwid_uuid}' for RemnaUser '{remna_id}'. "
                f"Total devices now: {response.total}"
            )
        except NotFoundError:
            logger.debug(f"RemnaUser '{remna_id}' not found in panel")
            return None

        return int(response.total)

    async def delete_all_devices(self, remna_id: int) -> None:
        try:
            result = await self.sdk.hwid.delete_all_hwid_user(
                DeleteUserAllHwidDeviceRequestDto(user_id=remna_id)
            )
        except NotFoundError:
            logger.debug(f"RemnaUser '{remna_id}' not found in panel")
            return
        logger.info(f"Deleted all HWID devices ({result.total}) for RemnaUser '{remna_id}'")

    async def drop_connections(self, remna_id: int) -> None:
        try:
            await self.sdk.connections.drop_connections(
                body=DropConnectionsRequestDto(
                    drop_by=DropByUserIds(user_ids=[remna_id]),
                    target_nodes=TargetAllNodes(),
                )
            )
            logger.info(f"Dropped connections for RemnaUser '{remna_id}'")
        except Exception as e:
            logger.warning(f"Failed to drop connections for RemnaUser '{remna_id}': {e}")

    async def reset_traffic(self, remna_id: int) -> Optional[UserResponseDto]:
        try:
            remna_user = await self.sdk.users.reset_user_traffic(remna_id)
            logger.info(f"Traffic for RemnaUser '{remna_user.id}' reset successfully")
            return remna_user
        except NotFoundError:
            logger.debug(f"RemnaUser '{remna_id}' not found in panel")
            return None

    async def revoke_subscription(self, remna_id: int) -> Optional[str]:
        try:
            result = await self.sdk.users.revoke_user_subscription(remna_id)
            logger.info(f"Subscription for RemnaUser '{remna_id}' revoked successfully")
            return result.subscription_url
        except NotFoundError:
            logger.debug(f"RemnaUser '{remna_id}' not found in panel")
            return None

    async def get_squads_available(self) -> bool:
        result = await self.sdk.internal_squads.get_internal_squads()
        return bool(result.internal_squads)

    async def get_internal_squads(self) -> list[SquadInfoDto]:
        result = await self.sdk.internal_squads.get_internal_squads()
        return [SquadInfoDto(uuid=s.uuid, name=s.name) for s in result.internal_squads]

    async def get_external_squads(self) -> list[SquadInfoDto]:
        result = await self.sdk.external_squads.get_external_squads()
        return [SquadInfoDto(uuid=s.uuid, name=s.name) for s in result.external_squads]

    def apply_sync(self, target: T, source: Union[SubscriptionDto, RemnaSubscriptionDto]) -> T:
        if not is_dataclass(target) or not is_dataclass(source):
            raise TypeError("Both target and source must be dataclasses")

        target_fields = {f.name for f in fields(target)}
        source_fields = {f.name for f in fields(source)}

        # `user_remna_id` used to be mapped from the panel's `uuid`; since 3.x
        # both sides name the panel identity `user_remna_id`, so the plain
        # common-field pass below covers it.
        common_fields = target_fields & source_fields

        for field_name in common_fields:
            old_value = getattr(target, field_name)
            new_value = getattr(source, field_name)

            if old_value != new_value:
                logger.debug(f"Field '{field_name}' changed from '{old_value}' to '{new_value}'")
                setattr(target, field_name, new_value)

        return target

    def _build_create_request(
        self,
        user: UserDto,
        plan: Optional[PlanSnapshotDto],
        subscription: Optional[SubscriptionDto],
    ) -> CreateUserRequestDto:
        if subscription:
            # Panel 3.x assigns the user id itself: `CreateUserRequestDto` no
            # longer accepts a caller-supplied identity, so the caller must
            # persist `user_remna_id` from the response.
            return CreateUserRequestDto(
                username=user.remna_name,
                telegram_id=user.telegram_id,
                expire_at=subscription.expire_at,
                traffic_limit_strategy=subscription.traffic_limit_strategy,
                traffic_limit_bytes=gb_to_bytes(subscription.traffic_limit),
                hwid_device_limit=subscription.device_limit,
                description=user.remna_description,
                email=user.email,
                tag=subscription.tag,
                active_internal_squads=subscription.internal_squads,
                external_squad_uuid=subscription.external_squad,
            )

        if plan:
            return CreateUserRequestDto(
                username=user.remna_name,
                telegram_id=user.telegram_id,
                expire_at=days_to_datetime(plan.duration),
                traffic_limit_strategy=plan.traffic_limit_strategy,
                traffic_limit_bytes=gb_to_bytes(plan.traffic_limit),
                hwid_device_limit=plan.device_limit,
                description=user.remna_description,
                email=user.email,
                tag=plan.tag,
                active_internal_squads=plan.internal_squads,
                external_squad_uuid=plan.external_squad,
            )

        return CreateUserRequestDto(
            username=user.remna_name,
            telegram_id=user.telegram_id,
            expire_at=datetime_now() + timedelta(days=3650),
            description=user.remna_description,
            email=user.email,
        )

    @staticmethod
    def _panel_status(subscription: SubscriptionDto) -> Optional[SubscriptionStatus]:
        """Status to send to the panel, or `None` to leave it to the panel.

        Panel 3.x accepts only ACTIVE and DISABLED on update — it derives
        LIMITED and EXPIRED itself and rejects them being set by hand (error
        A089). Sending ACTIVE for a subscription whose `expire_at` is already
        in the past is exactly that contradiction, and the panel answers 400.
        Omitting the field lets it keep deriving EXPIRED from `expire_at`,
        while every other field still gets pushed.

        It goes by the date being sent, not by the status stored in the bot: a
        renewal of an expired subscription still has EXPIRED stored while its
        new `expire_at` is in the future, and that is an ACTIVE subscription.
        """
        if subscription.status == SubscriptionStatus.DISABLED:
            return SubscriptionStatus.DISABLED
        if subscription.expire_at <= datetime_now():
            return None
        return SubscriptionStatus.ACTIVE

    def _build_update_request(
        self,
        user: UserDto,
        remna_id: int,
        plan: Optional[PlanSnapshotDto],
        subscription: Optional[SubscriptionDto],
    ) -> UpdateUserRequestDto:
        if subscription:
            status = self._panel_status(subscription)
            return UpdateUserRequestDto(
                id=remna_id,
                telegram_id=user.telegram_id,
                expire_at=subscription.expire_at,
                # the SDK sends every field that was set, so `status=None` would arrive as
                # null, which the panel rejects: leaving it to the panel means not setting it
                **({"status": status} if status else {}),
                traffic_limit_strategy=subscription.traffic_limit_strategy,
                traffic_limit_bytes=gb_to_bytes(subscription.traffic_limit),
                hwid_device_limit=subscription.device_limit,
                description=user.remna_description,
                email=user.email,
                tag=subscription.tag,
                active_internal_squads=subscription.internal_squads,
                external_squad_uuid=subscription.external_squad,
            )

        if plan:
            return UpdateUserRequestDto(
                id=remna_id,
                telegram_id=user.telegram_id,
                expire_at=days_to_datetime(plan.duration),
                status=SubscriptionStatus.ACTIVE,
                traffic_limit_strategy=plan.traffic_limit_strategy,
                traffic_limit_bytes=gb_to_bytes(plan.traffic_limit),
                hwid_device_limit=plan.device_limit,
                description=user.remna_description,
                email=user.email,
                tag=plan.tag,
                active_internal_squads=plan.internal_squads,
                external_squad_uuid=plan.external_squad,
            )

        raise ValueError("Either 'plan' or 'subscription' must be provided")
