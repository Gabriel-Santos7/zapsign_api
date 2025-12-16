from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class SignatureProviderStrategy(ABC):
    @abstractmethod
    def create_document(
        self,
        name: str,
        url_pdf: str,
        signers: List[Dict],
        **kwargs
    ) -> Dict:
        pass

    @abstractmethod
    def get_document_status(self, token: str) -> Dict:
        pass

    @abstractmethod
    def add_signer(self, doc_token: str, signer_data: Dict) -> Dict:
        pass

    @abstractmethod
    def cancel_document(self, token: str) -> Dict:
        pass

    @abstractmethod
    def handle_webhook(self, payload: Dict) -> None:
        pass

    @abstractmethod
    def to_internal_status(self, provider_status: str) -> str:
        pass


