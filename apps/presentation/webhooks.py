import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from apps.domain.models import Document, Company, Signer
from apps.application.facades.signature_provider_facade import SignatureProviderFacade

logger = logging.getLogger('apps')


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
            
            event_type = payload.get('event') or payload.get('event_type')
            _process_webhook_event(document, event_type, payload)
            
        except Document.DoesNotExist:
            logger.warning(f'Document not found for token: {doc_token}')
        
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f'Error processing webhook: {str(e)}')
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


def _process_webhook_event(document: Document, event_type: str, payload: dict):
    if event_type == 'doc_signed':
        document.provider_status = 'signed'
        document.internal_status = 'signed'
        document.save()
    
    elif event_type == 'signer_signed':
        signer_data = payload.get('signer', {})
        signer_token = signer_data.get('token')
        if signer_token:
            try:
                signer = document.signers.get(token=signer_token)
                signer.status = 'signed'
                signer.save()
                
                all_signed = all(s.status == 'signed' for s in document.signers.all())
                if all_signed:
                    document.provider_status = 'signed'
                    document.internal_status = 'signed'
                else:
                    document.internal_status = 'in_progress'
                document.save()
            except Signer.DoesNotExist:
                pass
    
    elif event_type == 'signer_authentication_failed':
        signer_data = payload.get('unauthenticated_signer', {})
        signer_token = signer_data.get('token')
        if signer_token:
            try:
                signer = document.signers.get(token=signer_token)
                signer.status = 'rejected'
                signer.save()
            except Signer.DoesNotExist:
                pass
    
    elif event_type == 'email_bounce':
        email = payload.get('email')
        if email:
            try:
                signer = document.signers.get(email=email)
                signer.status = 'rejected'
                signer.save()
            except Signer.DoesNotExist:
                pass


