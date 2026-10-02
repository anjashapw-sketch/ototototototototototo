"""Pricing repository."""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Pricing


class PricingRepository:
    """Repository for country pricing."""

    DEFAULT_KEY = "DEFAULT"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_country(
        self, country_code: str
    ) -> Optional[Pricing]:
        """Get pricing for a country."""
        result = await self.session.execute(
            select(Pricing).where(
                Pricing.country_code ==
                country_code
            )
        )
        return result.scalar_one_or_none()

    async def get_default(self) -> Decimal:
        """Get default price (fallback)."""
        pricing = await self.get_by_country(
            self.DEFAULT_KEY
        )
        if pricing:
            return pricing.price
        return Decimal("100.00")

    async def get_price(
        self, country_code: str
    ) -> Decimal:
        """
        Get price for country.
        Falls back to default if not set.
        """
        pricing = await self.get_by_country(
            country_code
        )
        if pricing:
            return pricing.price
        return await self.get_default()

    async def set_price(
        self,
        country_code: str,
        country_name: str,
        price: Decimal
    ) -> Pricing:
        """Set or update country price."""
        pricing = await self.get_by_country(
            country_code
        )
        if pricing:
            await self.session.execute(
                update(Pricing)
                .where(
                    Pricing.country_code ==
                    country_code
                )
                .values(
                    price=price,
                    country_name=country_name
                )
            )
            return pricing
        else:
            pricing = Pricing(
                country_code=country_code,
                country_name=country_name,
                price=price
            )
            self.session.add(pricing)
            await self.session.flush()
            return pricing

    async def get_all(self) -> List[Pricing]:
        """Get all pricing entries."""
        result = await self.session.execute(
            select(Pricing).order_by(
                Pricing.country_name
            )
        )
        return list(result.scalars().all())