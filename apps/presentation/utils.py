from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger('apps')


def error_response(message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: dict = None) -> Response:
    response_data = {
        'error': message,
        'status': status_code
    }
    
    if details:
        response_data['details'] = details
    
    logger.error(f'Error response: {message} - {details}')
    
    return Response(response_data, status=status_code)


def success_response(data: dict, status_code: int = status.HTTP_200_OK) -> Response:
    response_data = {
        'data': data,
        'status': status_code
    }
    
    return Response(response_data, status=status_code)





