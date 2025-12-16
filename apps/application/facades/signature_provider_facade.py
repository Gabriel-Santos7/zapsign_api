import time
import logging
from typing import Dict, List, Optional
from apps.domain.models import Company
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

    def to_internal_status(self, company: Company, provider_status: str) -> str:
        strategy = self._get_strategy(company)
        return strategy.to_internal_status(provider_status)


