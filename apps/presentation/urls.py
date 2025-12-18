from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import ProviderViewSet, CompanyViewSet, DocumentViewSet, SignerViewSet
from .webhooks import webhook_handler

router = DefaultRouter()
router.register(r'providers', ProviderViewSet, basename='provider')
router.register(r'companies', CompanyViewSet, basename='company')

urlpatterns = [
    path('api-token-auth/', obtain_auth_token, name='api-token-auth'),
    path('', include(router.urls)),
    path('companies/<int:company_pk>/documents/', DocumentViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='company-documents'),
    path('companies/<int:company_pk>/documents/<int:pk>/', DocumentViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='company-document-detail'),
    path('companies/<int:company_pk>/documents/<int:pk>/analyze/', DocumentViewSet.as_view({
        'post': 'analyze'
    }), name='document-analyze'),
    path('companies/<int:company_pk>/documents/<int:pk>/insights/', DocumentViewSet.as_view({
        'get': 'insights'
    }), name='document-insights'),
    path('companies/<int:company_pk>/documents/<int:pk>/add_signer/', DocumentViewSet.as_view({
        'post': 'add_signer'
    }), name='document-add-signer'),
    path('companies/<int:company_pk>/documents/<int:pk>/cancel/', DocumentViewSet.as_view({
        'post': 'cancel'
    }), name='document-cancel'),
    path('companies/<int:company_pk>/documents/<int:pk>/refresh_status/', DocumentViewSet.as_view({
        'post': 'refresh_status'
    }), name='document-refresh-status'),
    path('companies/<int:company_pk>/documents/alerts/', DocumentViewSet.as_view({
        'get': 'alerts'
    }), name='document-alerts'),
    path('companies/<int:company_pk>/documents/metrics/', DocumentViewSet.as_view({
        'get': 'metrics'
    }), name='document-metrics'),
    path('companies/<int:company_pk>/documents/<int:document_pk>/signers/', SignerViewSet.as_view({
        'get': 'list'
    }), name='document-signers'),
    path('companies/<int:company_pk>/documents/<int:document_pk>/signers/<int:pk>/', SignerViewSet.as_view({
        'get': 'retrieve'
    }), name='signer-detail'),
    path('webhooks/<str:provider_code>/', webhook_handler, name='webhook-handler'),
]

