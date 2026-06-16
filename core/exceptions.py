from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class ResourceNotFoundException(APIException):
    status_code = 404
    default_code = 'RESOURCE_NOT_FOUND'
    default_detail = 'The requested resource was not found.'

class DuplicateResourceException(APIException):
    status_code = 409
    default_code = 'DUPLICATE_RESOURCE'
    default_detail = 'A resource with these details already exists.'

class InsufficientInventoryException(APIException):
    status_code = 422
    default_code = 'INSUFFICIENT_INVENTORY'
    default_detail = 'Insufficient inventory to perform this operation.'

class InvalidOperationException(APIException):
    status_code = 422
    default_code = 'INVALID_OPERATION'
    default_detail = 'This operation is not valid in the current state.'

class InsufficientStockForOrderException(APIException):
    status_code = 422
    default_code = 'INSUFFICIENT_STOCK_FOR_ORDER'
    default_detail = 'One or more items in the order do not have sufficient stock.'

    def __init__(self, short_items, detail=None, code=None):
        super().__init__(detail=detail, code=code)
        self.short_items = short_items

def custom_exception_handler(exc, context):
    # Call DRF's default exception handler first to get the standard response
    response = exception_handler(exc, context)

    request = context.get('request')
    path = request.path if request else ''
    timestamp = timezone.now().isoformat()

    if response is not None:
        status_code = response.status_code
        errors = []

        if status_code == 400:
            error_code = 'VALIDATION_FAILED'
            # Extract validation error messages
            detail = exc.detail if hasattr(exc, 'detail') else response.data
            if isinstance(detail, dict):
                for field, details in detail.items():
                    if isinstance(details, list):
                        for item in details:
                            errors.append({"field": str(field), "message": str(item)})
                    elif isinstance(details, dict):
                        errors.append({"field": str(field), "message": str(details)})
                    else:
                        errors.append({"field": str(field), "message": str(details)})
            elif isinstance(detail, list):
                for item in detail:
                    errors.append({"field": "non_field_errors", "message": str(item)})
            else:
                errors.append({"field": "non_field_errors", "message": str(detail)})
            message = "Validation failed"
        else:
            # Custom error codes mapping for other standard HTTP errors
            if hasattr(exc, 'default_code'):
                error_code = exc.default_code
            elif status_code == 401:
                error_code = 'NOT_AUTHENTICATED'
            elif status_code == 403:
                error_code = 'PERMISSION_DENIED'
            elif status_code == 404:
                error_code = 'RESOURCE_NOT_FOUND'
            elif status_code == 429:
                error_code = 'TOO_MANY_LOGIN_ATTEMPTS'
            else:
                error_code = getattr(exc, 'default_code', 'ERROR')

            # Message extraction
            detail = response.data
            if isinstance(detail, dict):
                message = detail.get('detail', str(exc))
            else:
                message = str(detail)

        response.data = {
            "timestamp": timestamp,
            "status": status_code,
            "error_code": error_code,
            "message": message,
            "path": path,
            "errors": errors
        }
        if hasattr(exc, 'short_items'):
            response.data['short_items'] = exc.short_items
        return response
    else:
        # Unhandled exceptions (HTTP 500)
        logger.exception("Unhandled exception occurred")
        return Response({
            "timestamp": timestamp,
            "status": 500,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": str(exc),
            "path": path,
            "errors": []
        }, status=500)
