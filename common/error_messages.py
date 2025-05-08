from agents.exceptions import ErrorCode

# Error message mapping
ERROR_MESSAGES = {
    # System level errors (10000-10099)
    ErrorCode.INTERNAL_ERROR: "Internal server error",
    ErrorCode.INVALID_PARAMETERS: "Invalid parameters",
    ErrorCode.RATELIMITER: "Too many requests, please try again later",

    # Authentication errors (10100-10199)
    ErrorCode.AUTH_ERROR: "Authentication failed",
    ErrorCode.TOKEN_EXPIRED: "Login session expired, please login again",
    ErrorCode.TOKEN_INVALID: "Invalid authentication token",
    ErrorCode.TOKEN_MISSING: "Please login first",
    ErrorCode.REFRESH_TOKEN_EXPIRED: "Login session expired, please login again",
    ErrorCode.REFRESH_TOKEN_INVALID: "Invalid refresh token",
    ErrorCode.UNAUTHORIZED: "Unauthorized access",

    # Permission errors (10200-10299)
    ErrorCode.PERMISSION_DENIED: "Permission denied",
    ErrorCode.TENANT_INVALID: "Invalid tenant information",
    ErrorCode.RESOURCE_NOT_FOUND: "Resource not found",

    # User related errors (10300-10399)
    ErrorCode.USER_NOT_FOUND: "User not found",
    ErrorCode.USER_ALREADY_EXISTS: "User already exists",
    ErrorCode.INVALID_CREDENTIALS: "Invalid username or password",
    ErrorCode.INVALID_EMAIL: "Invalid email format",

    # Wallet related errors (10400-10499)
    ErrorCode.WALLET_ERROR: "Wallet operation failed",
    ErrorCode.WALLET_SIGNATURE_INVALID: "Invalid wallet signature",
    ErrorCode.WALLET_NONCE_EXPIRED: "Signature nonce expired, please request again",

    # API related errors (10500-10599)
    ErrorCode.OPENAPI_ERROR: "API configuration error",
    ErrorCode.API_CALL_ERROR: "API call failed",
    ErrorCode.API_RESPONSE_ERROR: "API response error"
}


def get_error_message(error_code: ErrorCode, default_message: str = None) -> str:
    """
    Get error message for error code

    Args:
        error_code: Error code
        default_message: Default message to use if error code is not defined

    Returns:
        str: Error message
    """
    return ERROR_MESSAGES.get(error_code, default_message or f"Unknown error: {error_code}")
