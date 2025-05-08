import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.response import RestResponse
from agents.exceptions import ErrorCode
from agents.middleware.auth_middleware import get_current_user
from agents.models.db import get_db
from agents.models.models import VipPackage
from agents.protocol.schemas import VipPackageDTO, VipMembershipDTO, VipPackageCreateDTO
from agents.services.vip_service import VipService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/vip/level", summary="Get user VIP level")
async def get_user_vip_level(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get user VIP level"""
    try:
        vip_level = await VipService.get_user_vip_level(user["id"], session)
        return RestResponse(data={
            "level": vip_level.value,
            "name": vip_level.name,
            "description": vip_level.__doc__
        })
    except Exception as e:
        logger.error(f"Failed to get user VIP level: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg="Failed to get user VIP level"
        )

@router.get("/vip/packages", summary="Get VIP package list")
async def get_vip_packages(
    level: Optional[int] = Query(None, description="Membership level"),
    is_active: bool = Query(True, description="Whether to show only active packages"),
    session: AsyncSession = Depends(get_db)
):
    """Get VIP package list"""
    try:
        packages = await VipService.get_packages(level, is_active, session)
        return RestResponse(data=[VipPackageDTO.from_orm(p) for p in packages])
    except Exception as e:
        logger.error(f"Failed to get VIP package list: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg="Failed to get VIP package list"
        )

@router.post("/vip/packages", summary="Create VIP package")
async def create_vip_package(
    package: VipPackageCreateDTO,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Create VIP package"""
    try:
        # Check user permissions
        if not user.get("is_admin"):
            return RestResponse(
                code=ErrorCode.PERMISSION_DENIED,
                msg="No permission to create VIP package"
            )
        
        # Create package
        new_package = VipPackage(
            name=package.name,
            level=package.level,
            duration=package.duration,
            price=package.price,
            description=package.description,
            features=package.features
        )
        session.add(new_package)
        await session.flush()
        
        return RestResponse(data=VipPackageDTO.from_orm(new_package))
    except Exception as e:
        logger.error(f"Failed to create VIP package: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg="Failed to create VIP package"
        )

@router.get("/vip/membership", summary="Get VIP membership")
async def get_vip_membership(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """Get VIP membership"""
    try:
        membership = await VipService.get_user_active_membership(user["id"], session)
        if not membership:
            return RestResponse(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                msg="No active membership found"
            )
        return RestResponse(data=VipMembershipDTO.from_orm(membership))
    except Exception as e:
        logger.error(f"Failed to get VIP membership: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg="Failed to get VIP membership"
        ) 