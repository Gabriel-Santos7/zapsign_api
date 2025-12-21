from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes


@extend_schema(
    summary='Health Check',
    description='Verifica o status de saúde da API e a conectividade com o banco de dados.',
    tags=['Health'],
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {
                    'type': 'string',
                    'example': 'ok',
                    'description': 'Status geral da API'
                },
                'database': {
                    'type': 'string',
                    'example': 'healthy',
                    'description': 'Status da conexão com o banco de dados (healthy/unhealthy)'
                }
            }
        }
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return Response({
        "status": "ok",
        "database": db_status
    }, status=status.HTTP_200_OK)


