import pytest
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from apps.domain.models import Provider, Company, Document, Signer, DocumentAnalysis


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_with_token(user):
    token = Token.objects.create(user=user)
    return user, token


@pytest.mark.django_db
class TestProviderViewSet:
    def test_list_providers(self, api_client, user_with_token, provider):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get('/api/providers/')
        
        assert response.status_code == 200
        assert len(response.data['results']) >= 1

    def test_list_providers_requires_auth(self, api_client):
        response = api_client.get('/api/providers/')
        
        assert response.status_code == 401


@pytest.mark.django_db
class TestCompanyViewSet:
    def test_create_company(self, api_client, user_with_token, provider):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        data = {
            'name': 'New Company',
            'provider': provider.id,
            'api_token': 'test_token_123',
            'provider_config': {}
        }
        
        response = api_client.post('/api/companies/', data, format='json')
        
        assert response.status_code == 201
        assert response.data['name'] == 'New Company'

    def test_list_companies(self, api_client, user_with_token, company):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get('/api/companies/')
        
        assert response.status_code == 200
        assert len(response.data['results']) >= 1


@pytest.mark.django_db
class TestDocumentViewSet:
    @patch('apps.application.services.signature_service.SignatureProviderFacade')
    def test_create_document(self, mock_facade_class, api_client, user_with_token, company):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        mock_facade = Mock()
        mock_facade.create_document.return_value = {
            'open_id': '123',
            'token': 'test_token',
            'status': 'pending',
            'signers': [
                {
                    'name': 'Test Signer',
                    'email': 'signer@example.com',
                    'token': 'signer_token',
                    'sign_url': 'https://example.com/sign',
                    'status': 'new'
                }
            ]
        }
        mock_facade.to_internal_status.return_value = 'pending'
        mock_facade_class.return_value = mock_facade
        
        data = {
            'name': 'Test Document',
            'url_pdf': 'https://example.com/test.pdf',
            'signers': [
                {
                    'name': 'Test Signer',
                    'email': 'signer@example.com'
                }
            ]
        }
        
        response = api_client.post(f'/api/companies/{company.id}/documents/', data, format='json')
        
        assert response.status_code == 201
        assert response.data['name'] == 'Test Document'

    def test_list_documents(self, api_client, user_with_token, company, document):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get(f'/api/companies/{company.id}/documents/')
        
        assert response.status_code == 200
        assert len(response.data['results']) >= 1

    def test_get_document(self, api_client, user_with_token, company, document):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get(f'/api/companies/{company.id}/documents/{document.id}/')
        
        assert response.status_code == 200
        assert response.data['id'] == document.id

    @patch('apps.presentation.views.DocumentAnalysisService')
    def test_analyze_document(self, mock_service_class, api_client, user_with_token, company, document):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        # Create a real DocumentAnalysis instance for the serializer
        from apps.domain.models import DocumentAnalysis
        analysis = DocumentAnalysis.objects.create(
            document=document,
            missing_topics=[],
            summary='Test summary',
            insights={},
            model_used='spacy'
        )
        
        mock_service = Mock()
        mock_service.analyze_document.return_value = analysis
        mock_service_class.return_value = mock_service
        
        response = api_client.post(f'/api/companies/{company.id}/documents/{document.id}/analyze/')
        
        assert response.status_code == 200

    def test_get_insights_not_analyzed(self, api_client, user_with_token, company, document):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get(f'/api/companies/{company.id}/documents/{document.id}/insights/')
        
        assert response.status_code == 404

    def test_get_insights(self, api_client, user_with_token, company, document):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        DocumentAnalysis.objects.create(
            document=document,
            missing_topics=[],
            summary='Test summary',
            insights={}
        )
        
        response = api_client.get(f'/api/companies/{company.id}/documents/{document.id}/insights/')
        
        assert response.status_code == 200
        assert response.data['summary'] == 'Test summary'

    @patch('apps.application.services.signature_service.SignatureProviderFacade')
    def test_add_signer(self, mock_facade_class, api_client, user_with_token, company, document):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        # Document needs a token to add signer
        document.token = 'test_token'
        document.save()
        
        mock_facade = Mock()
        mock_facade.add_signer.return_value = {
            'token': 'new_signer_token',
            'sign_url': 'https://example.com/sign',
            'status': 'new'
        }
        mock_facade_class.return_value = mock_facade
        
        data = {
            'name': 'New Signer',
            'email': 'newsigner@example.com'
        }
        
        response = api_client.post(f'/api/companies/{company.id}/documents/{document.id}/add_signer/', data, format='json')
        
        assert response.status_code == 201
        assert response.data['name'] == 'New Signer'

    @patch('apps.application.services.signature_service.SignatureProviderFacade')
    def test_cancel_document(self, mock_facade_class, api_client, user_with_token, company, document):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        # Document needs a token to cancel
        document.token = 'test_token'
        document.save()
        
        mock_facade = Mock()
        mock_facade.cancel_document.return_value = {}
        mock_facade_class.return_value = mock_facade
        
        response = api_client.post(f'/api/companies/{company.id}/documents/{document.id}/cancel/')
        
        assert response.status_code == 200

    @patch('apps.application.services.signature_service.SignatureProviderFacade')
    def test_refresh_status(self, mock_facade_class, api_client, user_with_token, company, document):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        document.token = 'test_token'
        document.save()
        
        mock_facade = Mock()
        mock_facade.get_document_status.return_value = {
            'status': 'signed',
            'signers': []
        }
        mock_facade.to_internal_status.return_value = 'signed'
        mock_facade_class.return_value = mock_facade
        
        response = api_client.post(f'/api/companies/{company.id}/documents/{document.id}/refresh_status/')
        
        assert response.status_code == 200

    def test_get_alerts(self, api_client, user_with_token, company):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get(f'/api/companies/{company.id}/documents/alerts/')
        
        assert response.status_code == 200
        assert 'alerts' in response.data

    def test_get_metrics(self, api_client, user_with_token, company):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get(f'/api/companies/{company.id}/documents/metrics/')
        
        assert response.status_code == 200
        assert 'total_documents' in response.data


@pytest.mark.django_db
class TestSignerViewSet:
    def test_list_signers(self, api_client, user_with_token, company, document, signer):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get(f'/api/companies/{company.id}/documents/{document.id}/signers/')
        
        assert response.status_code == 200
        assert len(response.data['results']) >= 1

    def test_get_signer(self, api_client, user_with_token, company, document, signer):
        user, token = user_with_token
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        response = api_client.get(f'/api/companies/{company.id}/documents/{document.id}/signers/{signer.id}/')
        
        assert response.status_code == 200
        assert response.data['id'] == signer.id


@pytest.mark.django_db
class TestWebhookHandler:
    def test_webhook_handler(self, api_client, company, document):
        payload = {
            'event_type': 'doc_signed',
            'token': document.token,
            'status': 'signed'
        }
        
        response = api_client.post(f'/api/webhooks/zapsign/', payload, format='json')
        
        assert response.status_code == 200
        assert response.data['status'] == 'ok'

    def test_webhook_handler_without_token(self, api_client):
        payload = {
            'event_type': 'doc_signed'
        }
        
        response = api_client.post('/api/webhooks/zapsign/', payload, format='json')
        
        assert response.status_code == 200



