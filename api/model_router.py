import logging

from fastapi import APIRouter, Depends, Query, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession

from agents.common.error_messages import get_error_message
from agents.common.response import RestResponse
from agents.exceptions import ErrorCode
from agents.middleware.auth_middleware import get_current_user
from agents.models.db import get_db
from agents.protocol.schemas import ModelCreate, ModelUpdate, ModelDTO, List
from agents.services import model_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/models/create", summary="Create Model", response_model=RestResponse[ModelDTO])
async def create_model(
        model: ModelCreate,
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Create a new model
    
    Parameters:
    - **name**: Name of the model
    - **endpoint**: API endpoint of the model
    - **api_key**: Optional API key for authentication
    """
    try:
        result = await model_service.create_model(model, user, session)
        return RestResponse(data=result)
    except Exception as e:
        logger.error(f"Error while creating model: {e}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )

@router.put("/models/{model_id}", summary="Update Model", response_model=RestResponse[ModelDTO])
async def update_model(
        model_id: int = Path(..., description="ID of the model to update"),
        model: ModelUpdate = Body(..., description="Model update data"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Update an existing model
    
    Parameters:
    - **model_id**: ID of the model to update
    - **name**: Optional new name for the model
    - **endpoint**: Optional new endpoint for the model
    - **api_key**: Optional new API key for the model
    """
    try:
        result = await model_service.update_model(model_id, model, user, session)
        return RestResponse(data=result)
    except Exception as e:
        logger.error(f"Error while updating model {model_id}: {e}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )

@router.get("/models/list", summary="List Models", response_model=RestResponse[List[ModelDTO]])
async def list_models(
        include_public: bool = Query(True, description="Include public models"),
        only_official: bool = Query(False, description="Show only official models"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    List all accessible models
    
    Parameters:
    - **include_public**: Whether to include public models (default: True)
    - **only_official**: Whether to show only official models (default: False)
    """
    try:
        models = await model_service.list_models(user, include_public, only_official, session)
        return RestResponse(data=models)
    except Exception as e:
        logger.error(f"Error while listing models: {e}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )

@router.get("/models/{model_id}", summary="Get Model", response_model=RestResponse[ModelDTO])
async def get_model(
        model_id: int = Path(..., description="ID of the model to retrieve"),
        user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Get a specific model by ID
    
    Parameters:
    - **model_id**: ID of the model to retrieve
    """
    try:
        model = await model_service.get_model(model_id, user, session)
        return RestResponse(data=model)
    except Exception as e:
        logger.error(f"Error while getting model {model_id}: {e}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )