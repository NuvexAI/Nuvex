import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.error_messages import get_error_message
from agents.common.response import RestResponse
from agents.exceptions import CustomAgentException, ErrorCode
from agents.middleware.auth_middleware import get_current_user, get_optional_current_user
from agents.models.db import get_db
from agents.protocol.schemas import CategoryCreate, CategoryUpdate, CategoryDTO, CategoryType
from agents.services import category_service

router = APIRouter()
logger = logging.getLogger(__name__)


# @router.post("/categories/create", summary="Create Category", response_model=RestResponse[CategoryDTO])
async def create_category(
    category: CategoryCreate,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Create a new category
    
    Parameters:
    - **name**: Name of the category
    - **type**: Type of the category (agent or tool)
    - **description**: Optional description of the category
    """
    try:
        result = await category_service.create_category(category, user, session)
        return RestResponse(data=result)
    except CustomAgentException as e:
        logger.error(f"Error creating category: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=e.message)
    except Exception as e:
        logger.error(f"Unexpected error creating category: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


# @router.put("/categories/{category_id}", summary="Update Category")
async def update_category(
    category_id: int,
    category: CategoryUpdate,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Update an existing category
    
    Parameters:
    - **category_id**: ID of the category to update
    - **name**: Optional new name for the category
    - **description**: Optional new description for the category
    """
    try:
        result = await category_service.update_category(category_id, category, user, session)
        return RestResponse(data=result)
    except CustomAgentException as e:
        logger.error(f"Error updating category: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=e.message)
    except Exception as e:
        logger.error(f"Unexpected error updating category: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


# @router.delete("/categories/{category_id}", summary="Delete Category")
async def delete_category(
    category_id: int,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Delete a category
    
    Parameters:
    - **category_id**: ID of the category to delete
    """
    try:
        await category_service.delete_category(category_id, user, session)
        return RestResponse(data="ok")
    except CustomAgentException as e:
        logger.error(f"Error deleting category: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=e.message)
    except Exception as e:
        logger.error(f"Unexpected error deleting category: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/categories", summary="List Categories", response_model=RestResponse[List[CategoryDTO]])
async def list_categories(
    type: Optional[CategoryType] = Query(None, description="Filter categories by type"),
    user: Optional[dict] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    List all categories with optional type filter
    
    Parameters:
    - **type**: Optional filter for category type (agent or tool)
    """
    try:
        categories = await category_service.get_categories(type, user, session)
        return RestResponse(data=categories)
    except CustomAgentException as e:
        logger.error(f"Error listing categories: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=e.message)
    except Exception as e:
        logger.error(f"Unexpected error listing categories: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/categories/{category_id}", summary="Get Category")
async def get_category(
    category_id: int,
    user: Optional[dict] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get a specific category by ID
    
    Parameters:
    - **category_id**: ID of the category to retrieve
    """
    try:
        category = await category_service.get_category(category_id, user, session)
        return RestResponse(data=category)
    except CustomAgentException as e:
        logger.error(f"Error getting category: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=e.message)
    except Exception as e:
        logger.error(f"Unexpected error getting category: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        ) 