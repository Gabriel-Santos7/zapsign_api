import pytest
from django.contrib.auth.models import User
from apps.domain.models import Provider, Company, Document, Signer, DocumentAnalysis


@pytest.mark.django_db
class TestProvider:
    def test_create_provider(self):
        provider = Provider.objects.create(
            name='ZapSign',
            code='zapsign',
            api_base_url='https://sandbox.api.zapsign.com.br',
            is_active=True
        )
        assert provider.name == 'ZapSign'
        assert provider.code == 'zapsign'
        assert provider.is_active is True


@pytest.mark.django_db
class TestCompany:
    def test_create_company(self, provider):
        company = Company.objects.create(
            name='Test Company',
            provider=provider,
            api_token='test_token',
            provider_config={'retry_policy': {'max_retries': 3}}
        )
        assert company.name == 'Test Company'
        assert company.provider == provider
        assert company.provider_config['retry_policy']['max_retries'] == 3


@pytest.mark.django_db
class TestDocument:
    def test_create_document(self, company, user):
        document = Document.objects.create(
            company=company,
            name='Test Document',
            file_url='https://example.com/test.pdf',
            internal_status='pending',
            created_by=user
        )
        assert document.name == 'Test Document'
        assert document.company == company
        assert document.internal_status == 'pending'


@pytest.mark.django_db
class TestSigner:
    def test_create_signer(self, document):
        signer = Signer.objects.create(
            document=document,
            name='Test Signer',
            email='signer@example.com',
            status='pending'
        )
        assert signer.name == 'Test Signer'
        assert signer.document == document
        assert signer.status == 'pending'


