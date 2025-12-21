import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from apps.domain.models import Document, Company, Signer
from apps.application.facades.signature_provider_facade import SignatureProviderFacade

logger = logging.getLogger('apps')


@extend_schema(
    summary='Receber webhook do provedor',
    description='Endpoint público para recebimento de webhooks dos provedores de assinatura digital. Processa eventos como assinatura concluída, documento cancelado, etc.',
    tags=['Webhooks'],
    request={
        'application/json': {
            'type': 'object',
            'description': 'Payload do webhook do provedor',
            'examples': {
                'zapsign_webhook': {
                    'summary': 'Exemplo de webhook ZapSign',
                    'value': {
                        'token': 'abc123def456',
                        'doc': {
                            'token': 'abc123def456',
                            'status': 'signed'
                        },
                        'event': 'document.signed'
                    }
                }
            }
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'status': {
                    'type': 'string',
                    'example': 'ok'
                }
            }
        }
    },
    parameters=[
        {
            'name': 'provider_code',
            'in': 'path',
            'description': 'Código do provedor (ex: zapsign)',
            'required': True,
            'schema': {'type': 'string'}
        }
    ],
)
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_handler(request, provider_code):
    try:
        payload = request.data
        facade = SignatureProviderFacade()
        
        doc_token = payload.get('token') or payload.get('doc', {}).get('token')
        if not doc_token:
            logger.warning(f'Webhook received without document token: {payload}')
            return Response({'status': 'ok'}, status=status.HTTP_200_OK)
        
        try:
            document = Document.objects.get(token=doc_token)
            company = document.company
            api_token = company.api_token
            base_url = company.provider_config.get('api_base_url') or company.provider.api_base_url
            
            facade.handle_webhook(provider_code, payload, api_token, base_url)
            facade.process_webhook_event(document, payload)
            
        except Document.DoesNotExist:
            logger.warning(f'Document not found for token: {doc_token}')
        
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f'Error processing webhook: {str(e)}')
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


