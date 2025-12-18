import requests
import logging
from datetime import datetime
from typing import Dict, List
from apps.domain.interfaces.signature_provider_strategy import SignatureProviderStrategy

logger = logging.getLogger('apps')


class ZapSignStrategy(SignatureProviderStrategy):
    def __init__(self, api_token: str, base_url: str = None):
        self.api_token = api_token
        self.base_url = base_url or 'https://sandbox.api.zapsign.com.br'
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }

    def _serialize_datetime(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def _clean_payload(self, payload: Dict) -> Dict:
        cleaned = {}
        for key, value in payload.items():
            if isinstance(value, datetime):
                cleaned[key] = value.isoformat()
            elif isinstance(value, dict):
                cleaned[key] = self._clean_payload(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._clean_payload(item) if isinstance(item, dict) else self._serialize_datetime(item)
                    for item in value
                ]
            else:
                cleaned[key] = value
        return cleaned

    def create_document(
        self,
        name: str,
        url_pdf: str,
        signers: List[Dict],
        **kwargs
    ) -> Dict:
        url = f'{self.base_url}/api/v1/docs/'
        payload = {
            'name': name,
            'url_pdf': url_pdf,
            'signers': signers,
            **kwargs
        }
        
        # Clean payload to ensure datetime objects are serialized
        payload = self._clean_payload(payload)
        
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_detail = 'Unknown error'
            try:
                error_detail = response.json() if response.text else str(e)
            except:
                error_detail = response.text[:500] if response.text else str(e)
            logger.error(f'Error creating document in ZapSign: {e.response.status_code} - {error_detail}')
            raise Exception(f'Failed to create document in ZapSign: {e.response.status_code} - {error_detail}')
        except requests.exceptions.RequestException as e:
            logger.error(f'Error creating document in ZapSign: {str(e)}')
            raise Exception(f'Failed to create document in ZapSign: {str(e)}')

    def get_document_status(self, token: str) -> Dict:
        url = f'{self.base_url}/api/v1/documents/{token}/'
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'Error getting document status from ZapSign: {str(e)}')
            raise Exception(f'Failed to get document status from ZapSign: {str(e)}')

    def add_signer(self, doc_token: str, signer_data: Dict) -> Dict:
        url = f'{self.base_url}/api/v1/documents/{doc_token}/signers'
        
        # Clean signer_data to ensure datetime objects are serialized
        signer_data = self._clean_payload(signer_data)
        
        try:
            response = requests.post(url, json=signer_data, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'Error adding signer to ZapSign document: {str(e)}')
            raise Exception(f'Failed to add signer to ZapSign document: {str(e)}')

    def cancel_document(self, token: str) -> Dict:
        url = f'{self.base_url}/api/v1/documents/{token}/cancel/'
        
        try:
            response = requests.post(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f'Error cancelling document in ZapSign: {str(e)}')
            raise Exception(f'Failed to cancel document in ZapSign: {str(e)}')

    def handle_webhook(self, payload: Dict) -> None:
        event_type = payload.get('event_type') or payload.get('event')
        
        if event_type == 'doc_created':
            logger.info(f'Document created: {payload.get("token") or payload.get("doc", {}).get("token")}')
        elif event_type == 'doc_signed':
            logger.info(f'Document signed: {payload.get("token") or payload.get("doc", {}).get("token")}')
        elif event_type == 'signer_signed':
            signer_data = payload.get('signer', {})
            logger.info(f'Signer signed: {signer_data.get("email")}')
        elif event_type == 'signer_authentication_failed':
            signer_data = payload.get('unauthenticated_signer', {}) or payload.get('signer', {})
            logger.warning(f'Signer authentication failed: {signer_data.get("email")}')
        elif event_type == 'email_bounce':
            logger.warning(f'Email bounce: {payload.get("email")}')
        else:
            logger.info(f'Unknown webhook event: {event_type}')

    def to_internal_status(self, provider_status: str) -> str:
        mapping = {
            'pending': 'pending',
            'signed': 'signed',
            'cancelled': 'cancelled',
            'rejected': 'rejected',
            'expired': 'expired',
        }
        return mapping.get(provider_status.lower(), 'pending')


