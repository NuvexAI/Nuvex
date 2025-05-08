import logging
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from agents.common.error_messages import get_error_message
from agents.common.response import RestResponse
from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.db import get_db
from agents.services import file_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload/file", summary="Upload File")
async def upload_file(
        file: UploadFile = File(...),
        # user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Upload a file and store it using database storage.

    Parameters:
    - **file**: File to upload (form data)
    """
    try:
        if not file:
            raise CustomAgentException(
                ErrorCode.INVALID_PARAMETERS,
                "No file provided"
            )

        # if not user.get('tenant_id'):
        #     raise CustomAgentException(
        #         ErrorCode.UNAUTHORIZED,
        #         "User must belong to a tenant to upload files"
        #     )

        result = await file_service.upload_file(file, session)
        logger.info(f"File uploaded successfully: {result['fid']}")
        return RestResponse(data=result)
    except CustomAgentException as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=e.message)
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )


@router.get("/files/{fid}", summary="Get File")
async def get_file(
        fid: str,
        # user: dict = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """
    Get a file by its ID.

    Parameters:
    - **fid**: File ID to retrieve
    """
    try:
        # if not user.get('tenant_id'):
        #     raise CustomAgentException(
        #         ErrorCode.UNAUTHORIZED,
        #         "User must belong to a tenant to access files"
        #     )

        result = await file_service.query_file(fid, session)
        
        # Check if result is RedirectResponse (S3 presigned URL redirect)
        if hasattr(result, 'status_code') and hasattr(result, 'headers') and 'location' in result.headers:
            logger.info(f"Redirecting to S3 presigned URL for file: {fid}")
            return result  # Return RedirectResponse object directly
            
        # If it's a regular FileInfo object, process as usual
        file_record = result
        if not file_record:
            raise CustomAgentException(
                ErrorCode.RESOURCE_NOT_FOUND,
                "File not found"
            )

        logger.info(f"File retrieved successfully: {fid}")
        return StreamingResponse(
            iter([file_record['file_data']]),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=utf-8''{quote(file_record['file_name'])}",
                "Content-Length": str(file_record['file_size'])
            }
        )
    except CustomAgentException as e:
        logger.error(f"Error retrieving file {fid}: {str(e)}", exc_info=True)
        return RestResponse(code=e.error_code, msg=e.message)
    except Exception as e:
        logger.error(f"Unexpected error retrieving file {fid}: {str(e)}", exc_info=True)
        return RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg=get_error_message(ErrorCode.INTERNAL_ERROR)
        )
