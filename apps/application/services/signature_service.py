import logging
from typing import Dict, List, Optional
from django.contrib.auth.models import User
from apps.domain.models import Company, Document, Signer
from apps.application.facades.signature_provider_facade import SignatureProviderFacade

logger = logging.getLogger('apps')


class SignatureService:
    def __init__(self, facade: Optional[SignatureProviderFacade] = None):
        self.facade = facade or SignatureProviderFacade()

    def create_document(
        self,
        company: Company,
        name: str,
        url_pdf: str,
        signers_data: List[Dict],
        created_by: Optional[User] = None,
        **kwargs
    ) -> Document:
        response = self.facade.create_document(
            company=company,
            name=name,
            url_pdf=url_pdf,
            signers=signers_data,
            **kwargs
        )

        document = Document.objects.create(
            company=company,
            name=name,
            open_id=str(response.get('open_id', '')),
            token=response.get('token', ''),
            provider_status=response.get('status', ''),
            internal_status=self.facade.to_internal_status(company, response.get('status', 'pending')),
            file_url=url_pdf,
            date_limit_to_sign=kwargs.get('date_limit_to_sign'),
            created_by=created_by,
        )

        signers_response = response.get('signers', [])
        for signer_data in signers_response:
            Signer.objects.create(
                document=document,
                name=signer_data.get('name', ''),
                email=signer_data.get('email', ''),
                token=signer_data.get('token'),
                sign_url=signer_data.get('sign_url'),
                status=self._map_signer_status(signer_data.get('status', 'pending')),
            )

        return document

    def update_document_status(self, document: Document) -> Document:
        if not document.token:
            raise ValueError('Document token is required to update status')

        response = self.facade.get_document_status(document.company, document.token)
        
        document.provider_status = response.get('status', document.provider_status)
        document.internal_status = self.facade.to_internal_status(
            document.company,
            document.provider_status
        )
        
        signers_response = response.get('signers', [])
        for signer_data in signers_response:
            signer_token = signer_data.get('token')
            if signer_token:
                try:
                    signer = document.signers.get(token=signer_token)
                    signer.status = self._map_signer_status(signer_data.get('status', signer.status))
                    signer.save()
                except Signer.DoesNotExist:
                    pass

        document.save()
        return document

    def add_signer_to_document(
        self,
        document: Document,
        signer_data: Dict
    ) -> Signer:
        if not document.token:
            raise ValueError('Document token is required to add signer')

        response = self.facade.add_signer(document.company, document.token, signer_data)
        
        signer = Signer.objects.create(
            document=document,
            name=signer_data.get('name', ''),
            email=signer_data.get('email', ''),
            token=response.get('token'),
            sign_url=response.get('sign_url'),
            status=self._map_signer_status(response.get('status', 'pending')),
        )

        return signer

    def cancel_document(self, document: Document) -> Document:
        if not document.token:
            raise ValueError('Document token is required to cancel')

        self.facade.cancel_document(document.company, document.token)
        
        document.provider_status = 'cancelled'
        document.internal_status = 'cancelled'
        document.save()

        return document

    def _map_signer_status(self, provider_status: str) -> str:
        mapping = {
            'new': 'pending',
            'link-opened': 'in_progress',
            'signed': 'signed',
            'refused': 'rejected',
            'cancelled': 'cancelled',
        }
        return mapping.get(provider_status.lower(), 'pending')


