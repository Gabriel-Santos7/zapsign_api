import pytest
from unittest.mock import Mock, patch, MagicMock
from apps.application.services.signature_service import SignatureService
from apps.application.services.document_analysis_service import DocumentAnalysisService
from apps.application.facades.signature_provider_facade import SignatureProviderFacade


@pytest.mark.django_db
class TestSignatureService:
    @patch('apps.application.services.signature_service.SignatureProviderFacade')
    def test_create_document(self, mock_facade_class, company, user):
        mock_facade = Mock()
        mock_facade.create_document.return_value = {
            'open_id': '123',
            'token': 'test_token',
            'status': 'pending',
            'signers': []
        }
        mock_facade.to_internal_status.return_value = 'pending'
        mock_facade_class.return_value = mock_facade
        
        service = SignatureService(mock_facade)
        document = service.create_document(
            company=company,
            name='Test Doc',
            url_pdf='https://example.com/test.pdf',
            signers_data=[],
            created_by=user
        )
        
        assert document.name == 'Test Doc'
        assert document.token == 'test_token'

    @patch('apps.application.services.signature_service.SignatureProviderFacade')
    def test_update_document_status(self, mock_facade_class, document):
        mock_facade = Mock()
        mock_facade.get_document_status.return_value = {
            'status': 'signed',
            'signers': []
        }
        mock_facade.to_internal_status.return_value = 'signed'
        mock_facade_class.return_value = mock_facade
        
        document.token = 'test_token'
        document.save()
        
        service = SignatureService(mock_facade)
        updated_doc = service.update_document_status(document)
        
        assert updated_doc.internal_status == 'signed'


@pytest.mark.django_db
class TestDocumentAnalysisService:
    @patch('apps.application.services.document_analysis_service.PDFExtractorService')
    @patch('apps.application.services.document_analysis_service.spacy.load')
    def test_analyze_document(self, mock_spacy_load, mock_pdf_extractor_class, document):
        mock_pdf_extractor = Mock()
        mock_pdf_extractor.extract_text_from_url.return_value = 'Este é um documento de teste. Contém informações importantes sobre um contrato. O documento estabelece os termos e condições.'
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.__iter__ = Mock(return_value=iter([]))
        mock_doc.ents = []
        mock_doc.noun_chunks = []
        mock_sent1 = Mock()
        mock_sent1.text = 'Este é um documento de teste.'
        mock_sent2 = Mock()
        mock_sent2.text = 'Contém informações importantes sobre um contrato.'
        mock_sent3 = Mock()
        mock_sent3.text = 'O documento estabelece os termos e condições.'
        mock_doc.sents = [mock_sent1, mock_sent2, mock_sent3]
        mock_nlp.return_value = mock_doc
        mock_spacy_load.return_value = mock_nlp
        
        service = DocumentAnalysisService(mock_pdf_extractor)
        service.nlp = mock_nlp
        
        analysis = service.analyze_document(document)
        
        assert analysis.document == document
        assert analysis.summary is not None
        assert isinstance(analysis.missing_topics, list)
        assert isinstance(analysis.insights, dict)


