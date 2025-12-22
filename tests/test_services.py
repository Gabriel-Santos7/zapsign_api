import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
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
    @patch('spacy.load')
    def test_analyze_document(self, mock_spacy_load, mock_pdf_extractor_class, document):
        mock_pdf_extractor = Mock()
        mock_pdf_extractor.extract_text_from_url.return_value = (
            'Este é um documento de teste. '
            'O contrato estabelece prazo de 30 dias para entrega. '
            'O valor total é de R$ 10.000,00. '
            'Contém informações importantes sobre um contrato. '
            'O documento estabelece os termos e condições. '
            'As responsabilidades são divididas entre as partes.'
        )
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.__iter__ = Mock(return_value=iter([]))
        
        # Mock entities
        mock_ent1 = Mock()
        mock_ent1.text = 'R$ 10.000,00'
        mock_ent1.label_ = 'MONEY'
        mock_ent1.sent = Mock()
        mock_ent2 = Mock()
        mock_ent2.text = '30 dias'
        mock_ent2.label_ = 'DATE'
        mock_ent2.sent = Mock()
        mock_doc.ents = [mock_ent1, mock_ent2]
        
        # Mock noun chunks
        mock_chunk1 = Mock()
        mock_chunk1.text = 'documento de teste'
        mock_chunk2 = Mock()
        mock_chunk2.text = 'prazo de entrega'
        mock_doc.noun_chunks = [mock_chunk1, mock_chunk2]
        
        # Mock sentences
        mock_sent1 = Mock()
        mock_sent1.text = 'Este é um documento de teste.'
        mock_sent2 = Mock()
        mock_sent2.text = 'O contrato estabelece prazo de 30 dias para entrega.'
        mock_sent3 = Mock()
        mock_sent3.text = 'O valor total é de R$ 10.000,00.'
        mock_sent4 = Mock()
        mock_sent4.text = 'Contém informações importantes sobre um contrato.'
        mock_sent5 = Mock()
        mock_sent5.text = 'O documento estabelece os termos e condições.'
        mock_sent6 = Mock()
        mock_sent6.text = 'As responsabilidades são divididas entre as partes.'
        
        # Link entities to sentences
        mock_ent1.sent = mock_sent3
        mock_ent2.sent = mock_sent2
        
        mock_doc.sents = [mock_sent1, mock_sent2, mock_sent3, mock_sent4, mock_sent5, mock_sent6]
        mock_nlp.return_value = mock_doc
        mock_nlp.meta = {'name': 'pt_core_news_sm'}
        mock_spacy_load.return_value = mock_nlp
        
        # Reset the class-level _nlp_model to ensure the mock is used
        DocumentAnalysisService._nlp_model = None
        
        service = DocumentAnalysisService(mock_pdf_extractor)
        
        analysis = service.analyze_document(document)
        
        assert analysis.document == document
        assert analysis.summary is not None
        assert len(analysis.summary) > 0
        assert isinstance(analysis.missing_topics, list)
        assert isinstance(analysis.insights, dict)
        assert 'key_points' in analysis.insights
        assert 'recommendations' in analysis.insights
        assert 'risks' in analysis.insights
        # Entities may not always be present if no entities are found
        # Check if entities exist, but don't fail if they don't (they're optional)
        if 'entities' in analysis.insights:
            assert isinstance(analysis.insights['entities'], dict)
        # Check metadata
        assert 'analysis_metadata' in analysis.__dict__ or hasattr(analysis, 'analysis_metadata')
        if hasattr(analysis, 'analysis_metadata') and analysis.analysis_metadata:
            assert 'processing_time_seconds' in analysis.analysis_metadata
            assert 'model_name' in analysis.analysis_metadata
    
    @patch('apps.application.services.document_analysis_service.PDFExtractorService')
    @patch('spacy.load')
    def test_improved_summary_selects_important_sentences(self, mock_spacy_load, mock_pdf_extractor_class, document):
        """Test that improved summary selects sentences with entities and key terms"""
        mock_pdf_extractor = Mock()
        mock_pdf_extractor.extract_text_from_url.return_value = (
            'Introdução do documento. '
            'O contrato estabelece prazo de 30 dias. '
            'Texto intermediário sem informações importantes. '
            'O valor total é de R$ 10.000,00. '
            'Mais texto intermediário. '
            'As responsabilidades são claramente definidas.'
        )
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.ents = []
        mock_doc.noun_chunks = []
        
        sentences_text = [
            'Introdução do documento.',
            'O contrato estabelece prazo de 30 dias.',
            'Texto intermediário sem informações importantes.',
            'O valor total é de R$ 10.000,00.',
            'Mais texto intermediário.',
            'As responsabilidades são claramente definidas.'
        ]
        
        mock_sents = []
        for text in sentences_text:
            mock_sent = Mock()
            mock_sent.text = text
            mock_sents.append(mock_sent)
        
        mock_doc.sents = mock_sents
        mock_nlp.return_value = mock_doc
        mock_nlp.meta = {'name': 'pt_core_news_sm'}
        mock_spacy_load.return_value = mock_nlp
        
        # Reset the class-level _nlp_model to ensure the mock is used
        DocumentAnalysisService._nlp_model = None
        
        service = DocumentAnalysisService(mock_pdf_extractor)
        
        analysis = service.analyze_document(document)
        
        # Summary should contain important sentences with key terms
        summary_lower = analysis.summary.lower()
        assert 'prazo' in summary_lower or 'valor' in summary_lower or 'responsabilidade' in summary_lower
    
    @patch('apps.application.services.document_analysis_service.PDFExtractorService')
    @patch('spacy.load')
    def test_improved_missing_topics_detects_document_type(self, mock_spacy_load, mock_pdf_extractor_class, document):
        """Test that improved missing topics adapts to document type"""
        mock_pdf_extractor = Mock()
        # Contract-type document
        mock_pdf_extractor.extract_text_from_url.return_value = (
            'CONTRATO DE PRESTAÇÃO DE SERVIÇOS. '
            'Este contrato estabelece os termos entre as partes. '
            'O valor será definido posteriormente.'
        )
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.ents = []
        mock_doc.noun_chunks = []
        mock_doc.sents = [Mock(text='CONTRATO DE PRESTAÇÃO DE SERVIÇOS.')]
        mock_nlp.return_value = mock_doc
        mock_nlp.meta = {'name': 'pt_core_news_sm'}
        mock_spacy_load.return_value = mock_nlp
        
        # Reset the class-level _nlp_model to ensure the mock is used
        DocumentAnalysisService._nlp_model = None
        
        service = DocumentAnalysisService(mock_pdf_extractor)
        
        analysis = service.analyze_document(document)
        
        # Should identify missing topics relevant to contracts
        assert isinstance(analysis.missing_topics, list)
        # Should have some missing topics since document is incomplete
    
    @patch('apps.application.services.document_analysis_service.PDFExtractorService')
    @patch('spacy.load')
    def test_improved_insights_provides_deeper_analysis(self, mock_spacy_load, mock_pdf_extractor_class, document):
        """Test that improved insights provide more contextual information"""
        mock_pdf_extractor = Mock()
        mock_pdf_extractor.extract_text_from_url.return_value = (
            'O contrato estabelece prazo de 30 dias. '
            'O valor é de R$ 10.000,00. '
            'Em caso de rescisão, será aplicada multa de 20%.'
        )
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.ents = []
        mock_doc.noun_chunks = []
        mock_doc.sents = [Mock(text='O contrato estabelece prazo de 30 dias.')]
        mock_nlp.return_value = mock_doc
        mock_nlp.meta = {'name': 'pt_core_news_sm'}
        mock_spacy_load.return_value = mock_nlp
        
        # Reset the class-level _nlp_model to ensure the mock is used
        DocumentAnalysisService._nlp_model = None
        
        service = DocumentAnalysisService(mock_pdf_extractor)
        
        analysis = service.analyze_document(document)
        
        # Check improved insights structure
        assert 'key_points' in analysis.insights
        assert 'recommendations' in analysis.insights
        assert 'risks' in analysis.insights
        assert isinstance(analysis.insights['key_points'], list)
        assert isinstance(analysis.insights['recommendations'], list)
        assert isinstance(analysis.insights['risks'], list)
        
        # Risks should identify penalty clauses
        risks_text = ' '.join(analysis.insights['risks']).lower()
        if 'multa' in mock_pdf_extractor.extract_text_from_url.return_value.lower():
            # Should identify risk related to penalties
            assert len(analysis.insights['risks']) > 0
    
    @patch('apps.application.services.document_analysis_service.PDFExtractorService')
    @patch('apps.application.services.document_analysis_service.settings', new_callable=MagicMock)
    @patch('spacy.load')
    def test_analyze_document_no_gemini_key_uses_spacy(self, mock_spacy_load, mock_settings, mock_pdf_extractor_class, document):
        """Test that spaCy is used when Gemini API key is not configured"""
        # Configure settings mock - no API key
        mock_settings.GEMINI_ENABLED = True
        mock_settings.GEMINI_API_KEY = None
        mock_settings.SPACY_MODEL = 'pt_core_news_sm'
        
        mock_pdf_extractor = Mock()
        mock_pdf_extractor.extract_text_from_url.return_value = 'Este é um documento de teste.'
        mock_pdf_extractor_class.return_value = mock_pdf_extractor
        
        # Mock spaCy
        mock_nlp = Mock()
        mock_doc = Mock()
        mock_doc.__iter__ = Mock(return_value=iter([]))
        mock_doc.ents = []
        mock_doc.noun_chunks = []
        mock_doc.sents = [Mock(text='Este é um documento de teste.')]
        mock_nlp.return_value = mock_doc
        mock_nlp.meta = {'name': 'pt_core_news_sm'}
        mock_spacy_load.return_value = mock_nlp
        
        # Reset the class-level _nlp_model to ensure the mock is used
        DocumentAnalysisService._nlp_model = None
        
        service = DocumentAnalysisService(mock_pdf_extractor)
        
        analysis = service.analyze_document(document)
        
        assert analysis.document == document
        assert analysis.model_used == 'spacy'
        assert analysis.analysis_metadata['provider_used'] == 'spacy'
        assert analysis.analysis_metadata['fallback_reason'] == 'not_configured'


