import threading
import logging
from typing import Dict, Optional
from apps.domain.interfaces.signature_provider_strategy import SignatureProviderStrategy
from apps.domain.models import Provider, Company
from .zapsign_strategy import ZapSignStrategy

logger = logging.getLogger('apps')


class ProviderFactory:
    _instance = None
    _lock = threading.Lock()
    _providers_cache: Dict[str, SignatureProviderStrategy] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProviderFactory, cls).__new__(cls)
        return cls._instance

    def get_provider(self, provider_code: str, api_token: str, base_url: Optional[str] = None) -> SignatureProviderStrategy:
        cache_key = f'{provider_code}:{api_token}:{base_url or ""}'
        
        if cache_key not in self._providers_cache:
            with self._lock:
                if cache_key not in self._providers_cache:
                    strategy = self._create_strategy(provider_code, api_token, base_url)
                    self._providers_cache[cache_key] = strategy
        
        return self._providers_cache[cache_key]

    def get_provider_for_company(self, company: Company) -> SignatureProviderStrategy:
        provider = company.provider
        api_token = company.api_token
        base_url = company.provider_config.get('api_base_url') or provider.api_base_url
        
        return self.get_provider(provider.code, api_token, base_url)

    def _create_strategy(self, provider_code: str, api_token: str, base_url: Optional[str] = None) -> SignatureProviderStrategy:
        if provider_code.lower() == 'zapsign':
            return ZapSignStrategy(api_token, base_url)
        else:
            raise ValueError(f'Unknown provider code: {provider_code}')

    def clear_cache(self):
        with self._lock:
            self._providers_cache.clear()


