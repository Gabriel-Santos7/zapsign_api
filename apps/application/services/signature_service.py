import logging
import threading
from typing import Dict, List, Optional
from django.contrib.auth.models import User
from apps.domain.models import Company, Document, Signer
from apps.application.facades.signature_provider_facade import SignatureProviderFacade
from apps.application.services.document_analysis_service import DocumentAnalysisService

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
        save_as_draft: bool = False,
        **kwargs
    ) -> Document:
        if save_as_draft:
            # Criar como rascunho sem enviar para o provider
            document = Document.objects.create(
                company=company,
                name=name,
                open_id=None,
                token=None,
                provider_status=None,
                internal_status='draft',
                file_url=url_pdf,
                date_limit_to_sign=kwargs.get('date_limit_to_sign'),
                created_by=created_by,
            )

            # Criar signatários sem token/sign_url (serão criados quando enviar para assinatura)
            for signer_data in signers_data:
                Signer.objects.create(
                    document=document,
                    name=signer_data.get('name', ''),
                    email=signer_data.get('email', ''),
                    token=None,
                    sign_url=None,
                    status='pending',
                )

            logger.info(f'Document {document.id} created as draft')
            return document
        
        # Fluxo normal: enviar para o provider
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

        self._trigger_automatic_analysis(document)
        
        return document

    def _trigger_automatic_analysis(self, document: Document) -> None:
        def analyze_in_background():
            try:
                analysis_service = DocumentAnalysisService()
                analysis_service.analyze_document(document)
                logger.info(f'Automatic analysis completed for document {document.id}')
            except Exception as e:
                logger.error(f'Error in automatic analysis for document {document.id}: {str(e)}')
        
        thread = threading.Thread(target=analyze_in_background, daemon=True)
        thread.start()

    def update_document_status(self, document: Document) -> Document:
        if not document.token:
            raise ValueError('Document token is required to update status')

        try:
            response = self.facade.get_document_status(document.company, document.token)
        except Exception as e:
            # Se o documento não foi encontrado no provider, mantém o status atual
            if '404' in str(e) or 'not found' in str(e).lower():
                logger.warning(f'Document {document.token} not found in provider, keeping current status')
                return document
            # Para outros erros, propaga a exceção
            raise
        
        # Se o provider retornou 'not_found', mantém o status atual
        if response.get('status') == 'not_found':
            logger.warning(f'Document {document.token} not found in provider, keeping current status')
            return document
        
        document.provider_status = response.get('status', document.provider_status)
        
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
        
        # Se o documento está assinado no provider, atualiza todos os signatários pendentes
        if document.provider_status == 'signed':
            signers_updated = document.signers.filter(status__in=['pending', 'in_progress']).update(status='signed')
            if signers_updated > 0:
                logger.info(f'Updated {signers_updated} signer(s) to signed status during status refresh for document {document.token}')

        document.internal_status = self._calculate_internal_status(document, document.provider_status)
        document.save()
        return document

    def _calculate_internal_status(self, document: Document, provider_status: str) -> str:
        if provider_status in ['cancelled', 'rejected', 'expired']:
            return provider_status
        
        if provider_status == 'signed':
            all_signed = all(s.status == 'signed' for s in document.signers.all())
            return 'signed' if all_signed else 'in_progress'
        
        signed_count = sum(1 for s in document.signers.all() if s.status == 'signed')
        total_signers = document.signers.count()
        
        if signed_count > 0 and signed_count < total_signers:
            return 'in_progress'
        
        return self.facade.to_internal_status(document.company, provider_status)

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

    def send_draft_to_signature(self, document: Document) -> Document:
        """Envia um documento rascunho para assinatura no provider"""
        if document.internal_status != 'draft':
            raise ValueError('Only draft documents can be sent to signature')
        
        if not document.token:
            # Criar documento no provider
            signers_data = [
                {
                    'name': signer.name,
                    'email': signer.email
                }
                for signer in document.signers.all()
            ]
            
            response = self.facade.create_document(
                company=document.company,
                name=document.name,
                url_pdf=document.file_url,
                signers=signers_data,
                date_limit_to_sign=document.date_limit_to_sign
            )
            
            # Atualizar documento com dados do provider
            document.open_id = str(response.get('open_id', ''))
            document.token = response.get('token', '')
            document.provider_status = response.get('status', '')
            document.internal_status = self.facade.to_internal_status(
                document.company, 
                response.get('status', 'pending')
            )
            
            # Atualizar signatários com dados do provider
            signers_response = response.get('signers', [])
            for i, signer_data in enumerate(signers_response):
                if i < document.signers.count():
                    signer = document.signers.all()[i]
                    signer.token = signer_data.get('token')
                    signer.sign_url = signer_data.get('sign_url')
                    signer.status = self._map_signer_status(signer_data.get('status', 'pending'))
                    signer.save()
            
            document.save()
            logger.info(f'Draft document {document.id} sent to signature provider')
            
            # Disparar análise automática
            self._trigger_automatic_analysis(document)
        
        return document

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


