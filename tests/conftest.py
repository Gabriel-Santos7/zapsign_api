import pytest
from django.contrib.auth.models import User
from apps.domain.models import Provider, Company, Document, Signer


@pytest.fixture
def user():
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def provider():
    return Provider.objects.create(
        name='ZapSign',
        code='zapsign',
        api_base_url='https://sandbox.api.zapsign.com.br',
        is_active=True
    )


@pytest.fixture
def company(provider):
    return Company.objects.create(
        name='Test Company',
        provider=provider,
        api_token='test_token_123',
        provider_config={}
    )


@pytest.fixture
def document(company, user):
    return Document.objects.create(
        company=company,
        name='Test Document',
        file_url='https://example.com/test.pdf',
        internal_status='pending',
        created_by=user
    )


@pytest.fixture
def signer(document):
    return Signer.objects.create(
        document=document,
        name='Test Signer',
        email='signer@example.com',
        status='pending'
    )


