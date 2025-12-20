import time
import logging
from typing import Dict, List, Optional
from apps.domain.models import Company, Document, Signer
from apps.infrastructure.providers.factory import ProviderFactory
from apps.domain.interfaces.signature_provider_strategy import SignatureProviderStrategy

logger = logging.getLogger('apps')


class SignatureProviderFacade:
    def __init__(self, provider_factory: Optional[ProviderFactory] = None):
        self.provider_factory = provider_factory or ProviderFactory()

    def _get_strategy(self, company: Company) -> SignatureProviderStrategy:
        return self.provider_factory.get_provider_for_company(company)

    def _retry_operation(self, operation, max_retries: int = 3, delay: float = 1.0, **kwargs):
        retry_config = kwargs.pop('retry_config', {})
        max_retries = retry_config.get('max_retries', max_retries)
        delay = retry_config.get('delay', delay)
        
        for attempt in range(max_retries):
            try:
                return operation(**kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f'Retry attempt {attempt + 1}/{max_retries} failed: {str(e)}')
                time.sleep(delay * (attempt + 1))

    def create_document(
        self,
        company: Company,
        name: str,
        url_pdf: str,
        signers: List[Dict],
        **kwargs
    ) -> Dict:
        strategy = self._get_strategy(company)
        retry_config = company.provider_config.get('retry_policy', {})
        
        return self._retry_operation(
            strategy.create_document,
            retry_config=retry_config,
            name=name,
            url_pdf=url_pdf,
            signers=signers,
            **kwargs
        )

    def get_document_status(self, company: Company, doc_token: str) -> Dict:
        strategy = self._get_strategy(company)
        retry_config = company.provider_config.get('retry_policy', {})
        
        return self._retry_operation(
            strategy.get_document_status,
            retry_config=retry_config,
            token=doc_token
        )

    def add_signer(self, company: Company, doc_token: str, signer_data: Dict) -> Dict:
        strategy = self._get_strategy(company)
        retry_config = company.provider_config.get('retry_policy', {})
        
        return self._retry_operation(
            strategy.add_signer,
            retry_config=retry_config,
            doc_token=doc_token,
            signer_data=signer_data
        )

    def cancel_document(self, company: Company, doc_token: str) -> Dict:
        strategy = self._get_strategy(company)
        retry_config = company.provider_config.get('retry_policy', {})
        
        return self._retry_operation(
            strategy.cancel_document,
            retry_config=retry_config,
            token=doc_token
        )

    def handle_webhook(self, provider_code: str, payload: Dict, api_token: str, base_url: Optional[str] = None) -> None:
        strategy = self.provider_factory.get_provider(provider_code, api_token, base_url)
        strategy.handle_webhook(payload)

    def process_webhook_event(self, document: Document, payload: Dict) -> None:
        event_type = payload.get('event_type') or payload.get('event')
        
        if not event_type:
            logger.warning(f'Webhook received without event type: {payload}')
            return
        
        if event_type == 'doc_created':
            logger.info(f'Document created: {document.token}')
            document.provider_status = payload.get('status', 'pending')
            document.internal_status = self.to_internal_status(document.company, document.provider_status)
            document.save()
        
        elif event_type == 'doc_signed':
            document.provider_status = 'signed'
            document.internal_status = 'signed'
            document.save()
            
            # Atualiza todos os signatários para "signed" quando o documento é assinado
            signers_updated = document.signers.filter(status__in=['pending', 'in_progress']).update(status='signed')
            if signers_updated > 0:
                logger.info(f'Updated {signers_updated} signer(s) to signed status for document {document.token}')
            
            logger.info(f'Document signed: {document.token}')
        
        elif event_type == 'signer_signed':
            signer_data = payload.get('signer', {})
            signer_token = signer_data.get('token')
            if signer_token:
                try:
                    signer = document.signers.get(token=signer_token)
                    signer.status = 'signed'
                    signer.save()
                    logger.info(f'Signer signed: {signer.email} (token: {signer_token})')
                    
                    # Verifica se todos os signatários assinaram
                    all_signed = all(s.status == 'signed' for s in document.signers.all())
                    if all_signed:
                        document.provider_status = 'signed'
                        document.internal_status = 'signed'
                        logger.info(f'All signers signed. Document {document.token} status updated to signed')
                    else:
                        document.internal_status = 'in_progress'
                        pending_count = document.signers.exclude(status='signed').count()
                        logger.info(f'Document {document.token} status updated to in_progress ({pending_count} signer(s) pending)')
                    
                    document.save()
                except Signer.DoesNotExist:
                    logger.warning(f'Signer not found for token: {signer_token}')
        
        elif event_type == 'signer_authentication_failed':
            signer_data = payload.get('unauthenticated_signer', {})
            signer_token = signer_data.get('token')
            if signer_token:
                try:
                    signer = document.signers.get(token=signer_token)
                    signer.status = 'rejected'
                    signer.save()
                    logger.warning(f'Signer authentication failed: {signer.email}')
                except Signer.DoesNotExist:
                    logger.warning(f'Signer not found for token: {signer_token}')
        
        elif event_type == 'email_bounce':
            email = payload.get('email')
            if email:
                try:
                    signer = document.signers.get(email=email)
                    signer.status = 'rejected'
                    signer.save()
                    logger.warning(f'Email bounce for signer: {email}')
                except Signer.DoesNotExist:
                    logger.warning(f'Signer not found for email: {email}')
        
        else:
            logger.info(f'Unknown webhook event type: {event_type}')

    def to_internal_status(self, company: Company, provider_status: str) -> str:
        strategy = self._get_strategy(company)
        return strategy.to_internal_status(provider_status)


