"""
Live exchange rate service.
Fetches USD → INR rate from exchangerate-api.com (free, no key).
Falls back to manual rate if API fails.
"""

import asyncio
from datetime import datetime, timedelta

import aiohttp

from bot.database.engine import get_session
from bot.database.repositories.settings_repo import (
    SettingsRepository,
)
from bot.utils.logger import log


# ── Config ──
API_URL = "https://api.exchangerate-api.com/v4/latest/USD"
CACHE_TTL_MINUTES = 60  # 1 hour
FALLBACK_RATE = 83.0    # Default INR per USD


# ── Simple in-memory cache ──
_cache: dict = {
    "rate": None,
    "fetched_at": None,
}


async def get_usdt_inr_rate() -> float:
    """
    Get live USDT → INR rate.

    Flow:
      1. Check admin setting `usdt_rate_mode`:
         - "auto"  → fetch from API
         - "manual" → use `usdt_rate` setting
      2. For auto: check 1-hour cache first
      3. If API fails, fallback to manual rate
    """

    async with get_session() as session:
        repo = SettingsRepository(session)
        mode = await repo.get("usdt_rate_mode") or "auto"
        manual_rate = await repo.get_float(
            "usdt_rate", default=FALLBACK_RATE
        )

    # ── Manual mode ──
    if mode == "manual":
        log.info(f"📊 Using manual rate: ₹{manual_rate}")
        return manual_rate

    # ── Auto mode: check cache ──
    now = datetime.utcnow()
    if (
        _cache["rate"] is not None
        and _cache["fetched_at"] is not None
        and now - _cache["fetched_at"]
        < timedelta(minutes=CACHE_TTL_MINUTES)
    ):
        log.info(
            f"📊 Cached rate: ₹{_cache['rate']} "
            f"(fetched {int((now - _cache['fetched_at']).total_seconds())}s ago)"
        )
        return _cache["rate"]

    # ── Fetch fresh rate ──
    try:
        rate = await _fetch_live_rate()
        _cache["rate"] = rate
        _cache["fetched_at"] = now
        log.info(f"✅ Live rate fetched: 1 USDT = ₹{rate}")

        # Save in DB for reference
        async with get_session() as session:
            repo = SettingsRepository(session)
            await repo.set("usdt_rate_live", str(rate))
            await repo.set(
                "usdt_rate_last_update",
                now.isoformat(),
            )

        return rate

    except Exception as e:
        log.error(f"❌ Live rate fetch failed: {e}")

        # Try stale cache
        if _cache["rate"] is not None:
            log.warning(
                f"⚠️ Using stale cache: ₹{_cache['rate']}"
            )
            return _cache["rate"]

        # Final fallback: manual
        log.warning(
            f"⚠️ Using fallback rate: ₹{manual_rate}"
        )
        return manual_rate


async def _fetch_live_rate() -> float:
    """Fetch USD → INR from exchangerate-api.com."""

    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(API_URL) as resp:
            if resp.status != 200:
                raise RuntimeError(
                    f"API returned {resp.status}"
                )

            data = await resp.json()
            rates = data.get("rates", {})
            inr_rate = rates.get("INR")

            if not inr_rate:
                raise RuntimeError("INR not in API response")

            return float(inr_rate)


async def refresh_rate_cache() -> None:
    """Force refresh cache (for admin use)."""
    _cache["rate"] = None
    _cache["fetched_at"] = None
    await get_usdt_inr_rate()