import pytest
from apps.infrastructure.providers.factory import ProviderFactory
from apps.infrastructure.providers.zapsign_strategy import ZapSignStrategy
from apps.domain.interfaces.signature_provider_strategy import SignatureProviderStrategy
from apps.application.facades.signature_provider_facade import SignatureProviderFacade


@pytest.mark.django_db
class TestSingletonPattern:
    def test_provider_factory_singleton(self):
        factory1 = ProviderFactory()
        factory2 = ProviderFactory()
        assert factory1 is factory2

    def test_provider_factory_cache(self, provider):
        factory = ProviderFactory()
        strategy1 = factory.get_provider('zapsign', 'token1')
        strategy2 = factory.get_provider('zapsign', 'token1')
        assert strategy1 is strategy2


@pytest.mark.django_db
class TestStrategyPattern:
    def test_zapsign_strategy_implements_interface(self):
        strategy = ZapSignStrategy('test_token')
        assert isinstance(strategy, SignatureProviderStrategy)

    def test_strategy_lsp_substitution(self):
        strategy = ZapSignStrategy('test_token')
        assert isinstance(strategy, SignatureProviderStrategy)
        
        def use_strategy(s: SignatureProviderStrategy):
            return s.to_internal_status('pending')
        
        result = use_strategy(strategy)
        assert result == 'pending'


@pytest.mark.django_db
class TestFacadePattern:
    def test_facade_uses_strategy(self, company):
        facade = SignatureProviderFacade()
        assert facade is not None
        
        internal_status = facade.to_internal_status(company, 'pending')
        assert internal_status == 'pending'


@pytest.mark.django_db
class TestSOLID:
    def test_srp_provider_factory(self):
        factory = ProviderFactory()
        assert hasattr(factory, 'get_provider')
        assert hasattr(factory, 'get_provider_for_company')

    def test_ocp_extensibility(self):
        strategy = ZapSignStrategy('test_token')
        assert isinstance(strategy, SignatureProviderStrategy)

    def test_lsp_substitution(self):
        strategy = ZapSignStrategy('test_token')
        assert isinstance(strategy, SignatureProviderStrategy)

    def test_isp_interface_segregation(self):
        strategy = ZapSignStrategy('test_token')
        assert hasattr(strategy, 'create_document')
        assert hasattr(strategy, 'get_document_status')
        assert hasattr(strategy, 'add_signer')
        assert hasattr(strategy, 'cancel_document')
        assert hasattr(strategy, 'handle_webhook')
        assert hasattr(strategy, 'to_internal_status')

    def test_dip_dependency_inversion(self, company):
        facade = SignatureProviderFacade()
        assert facade is not None
        
        strategy = facade._get_strategy(company)
        assert isinstance(strategy, SignatureProviderStrategy)


