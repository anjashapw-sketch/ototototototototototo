"""Force subscription repository."""

from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    ForceSubChannel, ChannelType
)


class ForceSubRepository:
    """Repository for force sub channels."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        type: ChannelType,
        chat_id: int,
        invite_link: str,
        added_by: int,
        username: Optional[str] = None,
        is_bot_admin: bool = False
    ) -> ForceSubChannel:
        """Add new force sub channel."""
        channel = ForceSubChannel(
            name=name,
            type=type,
            chat_id=chat_id,
            username=username,
            invite_link=invite_link,
            is_bot_admin=is_bot_admin,
            added_by=added_by
        )
        self.session.add(channel)
        await self.session.flush()
        return channel

    async def get_by_id(
        self, channel_id: int
    ) -> Optional[ForceSubChannel]:
        """Get channel by internal ID."""
        result = await self.session.execute(
            select(ForceSubChannel).where(
                ForceSubChannel.id == channel_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_chat_id(
        self, chat_id: int
    ) -> Optional[ForceSubChannel]:
        """Get channel by Telegram chat ID."""
        result = await self.session.execute(
            select(ForceSubChannel).where(
                ForceSubChannel.chat_id == chat_id
            )
        )
        return result.scalar_one_or_none()

    async def get_all_active(
        self
    ) -> List[ForceSubChannel]:
        """Get all active channels."""
        result = await self.session.execute(
            select(ForceSubChannel)
            .where(
                ForceSubChannel.is_active == True
            )
            .order_by(ForceSubChannel.added_date)
        )
        return list(result.scalars().all())

    async def get_all(
        self
    ) -> List[ForceSubChannel]:
        """Get all channels."""
        result = await self.session.execute(
            select(ForceSubChannel).order_by(
                ForceSubChannel.added_date
            )
        )
        return list(result.scalars().all())

    async def update_bot_admin_status(
        self, channel_id: int, is_admin: bool
    ) -> None:
        """Update bot admin status."""
        await self.session.execute(
            update(ForceSubChannel)
            .where(
                ForceSubChannel.id == channel_id
            )
            .values(is_bot_admin=is_admin)
        )

    async def update_invite_link(
        self, channel_id: int, invite_link: str
    ) -> None:
        """Update invite link."""
        await self.session.execute(
            update(ForceSubChannel)
            .where(
                ForceSubChannel.id == channel_id
            )
            .values(invite_link=invite_link)
        )

    async def deactivate(
        self, channel_id: int
    ) -> None:
        """Mark channel as inactive."""
        await self.session.execute(
            update(ForceSubChannel)
            .where(
                ForceSubChannel.id == channel_id
            )
            .values(is_active=False)
        )

    async def delete(
        self, channel_id: int
    ) -> bool:
        """Permanently delete channel."""
        result = await self.session.execute(
            delete(ForceSubChannel).where(
                ForceSubChannel.id == channel_id
            )
        )
        return result.rowcount > 0