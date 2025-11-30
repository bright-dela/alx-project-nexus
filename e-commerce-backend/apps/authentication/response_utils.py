from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import uuid



def success_response(message, data=None, status_code=status.HTTP_200_OK, metadata=None):
    """
    Generate a standardized success response.

    Args:
        message: Human-readable success message
        data: Primary response payload (optional)
        status_code: HTTP status code (default: 200)
        metadata: Additional metadata (optional)

    Returns:
        Response object with standardized format
    """

    response_data = {
        "message": message,
    }

    if data is not None:
        response_data["data"] = data

    # Build metadata
    response_metadata = {
        "timestamp": timezone.now().isoformat(),
        "request_id": str(uuid.uuid4()),
    }

    if metadata:
        response_metadata.update(metadata)

    response_data["metadata"] = response_metadata

    return Response(response_data, status=status_code)




def error_response(error_type, message, details=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Generate a standardized error response.

    Args:
        error_type: Error type or code
        message: Human-readable error description
        details: Specific error details or validation errors (optional)
        status_code: HTTP status code (default: 400)

    Returns:
        Response object with standardized error format
    """

    response_data = {
        "error": error_type,
        "message": message,
        "metadata": {
            "timestamp": timezone.now().isoformat(),
            "request_id": str(uuid.uuid4()),
        },
    }

    if details:
        response_data["details"] = details

    return Response(response_data, status=status_code)




def validation_error_response(validation_errors, message="Validation failed"):
    """
    Generate a standardized validation error response.

    Args:
        validation_errors: Dictionary of field-specific validation errors
        message: General error message (default: "Validation failed")

    Returns:
        Response object with standardized validation error format
    """

    return error_response(
        error_type="validation_error",
        message=message,
        details=validation_errors,
        status_code=status.HTTP_400_BAD_REQUEST,
    )




def authentication_error_response(message="Authentication failed"):
    """
    Generate a standardized authentication error response.

    Args:
        message: Error message (default: "Authentication failed")

    Returns:
        Response object for authentication errors
    """


    return error_response(
        error_type="authentication_error",
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED,
    )





def permission_error_response(message="Permission denied"):
    """
    Generate a standardized permission error response.

    Args:
        message: Error message (default: "Permission denied")

    Returns:
        Response object for permission errors
    """

    return error_response(
        error_type="permission_error",
        message=message,
        status_code=status.HTTP_403_FORBIDDEN,
    )





def not_found_response(message="Resource not found"):
    """
    Generate a standardized not found error response.

    Args:
        message: Error message (default: "Resource not found")

    Returns:
        Response object for not found errors
    """

    return error_response(
        error_type="not_found", 
        message=message, 
        status_code=status.HTTP_404_NOT_FOUND
    )
