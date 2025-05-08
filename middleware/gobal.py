import logging

import fastapi
from fastapi.responses import ORJSONResponse

from agents.common.http_utils import add_cors_headers
from agents.common.response import RestResponse
from agents.exceptions import ErrorCode, CustomAgentException

logger = logging.getLogger(__name__)


async def exception_handler(request: fastapi.Request, exc):
    """
    Global exception handler

    Handles the following types of exceptions:
    1. CustomAgentException: Business exceptions with custom error codes and messages
    2. Other exceptions: Returns internal error code with generic error message
    """
    if isinstance(exc, CustomAgentException):
        # Handle business exceptions with their own error codes and messages
        ret = RestResponse(
            code=exc.error_code,
            msg=exc.message,
            data=None
        )
    else:
        # Handle all other exceptions as internal errors
        logger.error(
            f"Unhandled exception in {request.method} {request.url.path}",
            exc_info=exc
        )
        ret = RestResponse(
            code=ErrorCode.INTERNAL_ERROR,
            msg="Internal server error",
            data=None
        )

    # Always return 200 status code, let frontend handle errors based on response code
    return add_cors_headers(ORJSONResponse(
        ret.model_dump(exclude_none=True),
        status_code=200
    ))
