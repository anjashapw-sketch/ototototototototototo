"""
Bulk upload processor.
Manages the bulk add state in memory.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pyrogram import Client

from bot.services.fingerprint import (
    DeviceFingerprint
)
from bot.utils.logger import log


@dataclass
class BulkSessionData:
    """Active bulk upload session state."""

    owner_id: int
    batch_id: int
    phones: List[str]
    total: int
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    current_index: int = 0
    current_phone: Optional[str] = None
    current_client: Optional[Client] = None
    current_hash: Optional[str] = None
    current_fingerprint: Optional[
        DeviceFingerprint
    ] = None
    failed_log: List[Dict] = field(
        default_factory=list
    )
    started: bool = False
    stopped: bool = False
    lock: asyncio.Lock = field(
        default_factory=asyncio.Lock
    )

    @property
    def pending(self) -> int:
        """Pending number count."""
        return self.total - (
            self.successful
            + self.failed
            + self.skipped
        )

    @property
    def progress_message_id(self) -> int:
        """Stored message ID for editing."""
        return getattr(
            self, "_msg_id", 0
        )

    @progress_message_id.setter
    def progress_message_id(
        self, value: int
    ) -> None:
        self._msg_id = value


class BulkProcessor:
    """
    In-memory bulk upload session manager.
    Tracks one active session per owner.
    """

    def __init__(self):
        self._sessions: Dict[
            int, BulkSessionData
        ] = {}
        self._global_lock = asyncio.Lock()

    async def create_session(
        self,
        owner_id: int,
        batch_id: int,
        phones: List[str]
    ) -> BulkSessionData:
        """Create a new bulk session."""
        async with self._global_lock:
            session = BulkSessionData(
                owner_id=owner_id,
                batch_id=batch_id,
                phones=phones,
                total=len(phones)
            )
            self._sessions[owner_id] = session
            log.info(
                f"📦 Bulk session created: "
                f"owner={owner_id}, "
                f"total={len(phones)}"
            )
            return session

    def get_session(
        self, owner_id: int
    ) -> Optional[BulkSessionData]:
        """Get active session for owner."""
        return self._sessions.get(owner_id)

    async def remove_session(
        self, owner_id: int
    ) -> None:
        """Remove session."""
        async with self._global_lock:
            session = self._sessions.pop(
                owner_id, None
            )
            if session and session.current_client:
                try:
                    await (
                        session.current_client
                        .disconnect()
                    )
                except Exception:
                    pass
            log.info(
                f"📦 Bulk session removed: "
                f"owner={owner_id}"
            )

    def is_anyone_running(self) -> bool:
        """Check if any owner has active bulk."""
        return any(
            s.started and not s.stopped
            for s in self._sessions.values()
        )

    def get_running_owner(
        self
    ) -> Optional[int]:
        """Get owner ID with active bulk."""
        for owner_id, s in self._sessions.items():
            if s.started and not s.stopped:
                return owner_id
        return None


# ━━━ SINGLETON ━━━
bulk_processor = BulkProcessor()