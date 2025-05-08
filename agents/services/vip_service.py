import logging
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.models import VipMembership, VipPackage
from agents.protocol.enums import VipLevel

logger = logging.getLogger(__name__)

class VipService:
    @staticmethod
    async def get_user_vip_level(user_id: int, session: AsyncSession) -> VipLevel:
        """Get user's VIP level"""
        membership = await VipService.get_user_active_membership(user_id, session)
        if not membership:
            return VipLevel.NORMAL
        return VipLevel(membership.level)

    @staticmethod
    async def get_user_active_membership(user_id: int, session: AsyncSession) -> Optional[VipMembership]:
        """Get user's current active membership"""
        result = await session.execute(
            select(VipMembership)
            .where(
                VipMembership.user_id == user_id,
                VipMembership.status == "active",
                VipMembership.expire_time > datetime.utcnow()
            )
            .order_by(VipMembership.expire_time.desc())
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_membership(user_id: int, package_id: int, session: AsyncSession) -> VipMembership:
        """Create membership"""
        # Get package info
        package = await session.get(VipPackage, package_id)
        if not package:
            raise CustomAgentException(ErrorCode.RESOURCE_NOT_FOUND, "Package not found")

        # Calculate expiration time
        start_time = datetime.utcnow()
        expire_time = start_time + timedelta(days=package.duration)

        # Create membership
        membership = VipMembership(
            user_id=user_id,
            level=package.level,
            start_time=start_time,
            expire_time=expire_time
        )
        session.add(membership)
        await session.flush()
        return membership

    @staticmethod
    async def get_packages(session: AsyncSession, level: Optional[int] = None, is_active: bool = True) -> List[VipPackage]:
        """Get membership package list"""
        query = select(VipPackage)
        if level is not None:
            query = query.where(VipPackage.level == level)
        if is_active:
            query = query.where(VipPackage.is_active == True)
        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def check_membership_access(user_id: int, session: AsyncSession) -> bool:
        """Check if user has membership access"""
        membership = await VipService.get_user_active_membership(user_id, session)
        return membership is not None 