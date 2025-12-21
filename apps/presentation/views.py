import logging
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from apps.domain.models import Provider, Company, Document, Signer, DocumentAnalysis
from apps.presentation.serializers import (
    ProviderSerializer, CompanySerializer, DocumentSerializer,
    DocumentCreateSerializer, SignerSerializer, DocumentAnalysisSerializer,
    AddSignerSerializer
)
from apps.application.services.signature_service import SignatureService
from apps.application.services.document_analysis_service import DocumentAnalysisService
from apps.presentation.alerts import get_document_alerts, get_document_metrics
from apps.presentation.utils import error_response

logger = logging.getLogger('apps')


@extend_schema(
    summary='Obter token de autenticação',
    description='Autentica um usuário com username e password e retorna um token de autenticação. Use este token no header "Authorization: Token <token>" para acessar os demais endpoints.',
    tags=['Autenticação'],
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'username': {
                    'type': 'string',
                    'description': 'Nome de usuário',
                    'example': 'admin'
                },
                'password': {
                    'type': 'string',
                    'format': 'password',
                    'description': 'Senha do usuário',
                    'example': 'senha123'
                }
            },
            'required': ['username', 'password']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'token': {
                    'type': 'string',
                    'description': 'Token de autenticação',
                    'example': '9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b'
                }
            }
        },
        400: {
            'type': 'object',
            'description': 'Credenciais inválidas ou campos faltando'
        }
    },
    examples=[
        OpenApiExample(
            'Autenticação bem-sucedida',
            value={
                'token': '9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b'
            },
            response_only=True
        )
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def custom_obtain_auth_token(request):
    """Wrapper para documentar o endpoint de autenticação"""
    from django.contrib.auth import authenticate
    from rest_framework.authtoken.models import Token
    
    username = request.data.get('username')
    password = request.data.get('password')
    
    if username is None or password is None:
        return Response(
            {'error': 'Por favor, forneça username e password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    
    if not user:
        return Response(
            {'error': 'Credenciais inválidas'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    token, created = Token.objects.get_or_create(user=user)
    return Response({'token': token.key}, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary='Listar provedores',
        description='Retorna uma lista de todos os provedores de assinatura digital ativos.',
        tags=['Providers'],
    ),
    retrieve=extend_schema(
        summary='Obter detalhes do provedor',
        description='Retorna os detalhes de um provedor específico.',
        tags=['Providers'],
    ),
)
class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Provider.objects.filter(is_active=True)
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]


@extend_schema_view(
    list=extend_schema(
        summary='Listar empresas',
        description='Retorna uma lista paginada de todas as empresas cadastradas.',
        tags=['Companies'],
    ),
    create=extend_schema(
        summary='Criar empresa',
        description='Cria uma nova empresa com configurações de provedor de assinatura.',
        tags=['Companies'],
    ),
    retrieve=extend_schema(
        summary='Obter detalhes da empresa',
        description='Retorna os detalhes de uma empresa específica.',
        tags=['Companies'],
    ),
    update=extend_schema(
        summary='Atualizar empresa',
        description='Atualiza todos os campos de uma empresa.',
        tags=['Companies'],
    ),
    partial_update=extend_schema(
        summary='Atualizar empresa parcialmente',
        description='Atualiza campos específicos de uma empresa.',
        tags=['Companies'],
    ),
    destroy=extend_schema(
        summary='Excluir empresa',
        description='Remove uma empresa do sistema.',
        tags=['Companies'],
    ),
)
class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Company.objects.all()


@extend_schema_view(
    list=extend_schema(
        summary='Listar documentos',
        description='Retorna uma lista paginada de documentos de uma empresa.',
        tags=['Documents'],
        parameters=[
            OpenApiParameter('company_pk', OpenApiTypes.INT, location=OpenApiParameter.PATH, description='ID da empresa'),
        ],
    ),
    create=extend_schema(
        summary='Criar documento',
        description='Cria um novo documento. Pode ser salvo como rascunho ou enviado diretamente para assinatura.',
        tags=['Documents'],
        request=DocumentCreateSerializer,
        responses={
            201: DocumentSerializer,
            400: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Criar documento para assinatura',
                value={
                    'name': 'Contrato de Prestação de Serviços',
                    'url_pdf': 'https://example.com/documento.pdf',
                    'signers': [
                        {'name': 'João Silva', 'email': 'joao@example.com'},
                        {'name': 'Maria Santos', 'email': 'maria@example.com'}
                    ],
                    'date_limit_to_sign': '2024-12-31T23:59:59Z',
                    'save_as_draft': False
                }
            ),
            OpenApiExample(
                'Criar documento como rascunho',
                value={
                    'name': 'Contrato de Prestação de Serviços',
                    'url_pdf': 'https://example.com/documento.pdf',
                    'signers': [
                        {'name': 'João Silva', 'email': 'joao@example.com'}
                    ],
                    'save_as_draft': True
                }
            ),
        ],
    ),
    retrieve=extend_schema(
        summary='Obter detalhes do documento',
        description='Retorna os detalhes completos de um documento, incluindo lista de signatários.',
        tags=['Documents'],
    ),
    update=extend_schema(
        summary='Atualizar documento',
        description='Atualiza todos os campos de um documento.',
        tags=['Documents'],
    ),
    partial_update=extend_schema(
        summary='Atualizar documento parcialmente',
        description='Atualiza campos específicos de um documento.',
        tags=['Documents'],
    ),
    destroy=extend_schema(
        summary='Excluir documento',
        description='Remove um documento do sistema.',
        tags=['Documents'],
    ),
)
class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company_id = self.kwargs.get('company_pk')
        return Document.objects.filter(company_id=company_id)

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentCreateSerializer
        return DocumentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        company_id = self.kwargs.get('company_pk')
        context['company'] = get_object_or_404(Company, pk=company_id)
        context['user'] = self.request.user
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary='Enviar rascunho para assinatura',
        description='Envia um documento que está em rascunho para o fluxo de assinatura. O documento deve ter pelo menos um signatário cadastrado.',
        tags=['Documents'],
        responses={
            200: DocumentSerializer,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
    )
    @action(detail=True, methods=['post'])
    def send_to_signature(self, request, company_pk=None, pk=None):
        """Envia um documento rascunho para assinatura"""
        document = self.get_object()
        try:
            service = SignatureService()
            document = service.send_draft_to_signature(document)
            return Response(DocumentSerializer(document).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Error sending draft to signature: {str(e)}')
            return error_response('Failed to send document to signature', status.HTTP_500_INTERNAL_SERVER_ERROR, {'detail': str(e)})

    @extend_schema(
        summary='Analisar documento com IA',
        description='Realiza análise inteligente do documento usando IA (spaCy e/ou Google Gemini). Extrai informações, identifica tópicos faltantes e gera insights sobre o conteúdo.',
        tags=['Documents'],
        responses={
            200: DocumentAnalysisSerializer,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
    )
    @action(detail=True, methods=['post'])
    def analyze(self, request, company_pk=None, pk=None):
        document = self.get_object()
        try:
            service = DocumentAnalysisService()
            analysis = service.analyze_document(document)
            return Response(DocumentAnalysisSerializer(analysis).data, status=status.HTTP_200_OK)
        except ValueError as e:
            # ValueError usually means user input issue (e.g., PDF download failed)
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_detail = str(e)
            # Provide more user-friendly error messages
            if 'download PDF' in error_detail or '403' in error_detail or '404' in error_detail:
                return error_response(
                    'Não foi possível baixar o PDF para análise. Verifique se a URL está acessível e se o arquivo existe.',
                    status.HTTP_400_BAD_REQUEST,
                    {'detail': error_detail, 'url': document.file_url}
                )
            elif 'spaCy model' in error_detail:
                return error_response(
                    'Modelo de análise não configurado. Por favor, instale um modelo spaCy.',
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    {'detail': error_detail}
                )
            else:
                return error_response(
                    'Falha ao analisar documento',
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    {'detail': error_detail}
                )

    @extend_schema(
        summary='Obter insights do documento',
        description='Retorna os insights e análise de um documento que já foi analisado. Se o documento ainda não foi analisado, retorna erro 404.',
        tags=['Documents'],
        responses={
            200: DocumentAnalysisSerializer,
            404: OpenApiTypes.OBJECT,
        },
    )
    @action(detail=True, methods=['get'])
    def insights(self, request, company_pk=None, pk=None):
        document = self.get_object()
        try:
            analysis = document.analysis
            return Response(DocumentAnalysisSerializer(analysis).data, status=status.HTTP_200_OK)
        except DocumentAnalysis.DoesNotExist:
            return error_response(
                'Documento ainda não foi analisado. Use o endpoint /analyze/ para realizar a análise.',
                status.HTTP_404_NOT_FOUND,
                {'document_id': document.id, 'document_name': document.name}
            )

    @extend_schema(
        summary='Adicionar signatário ao documento',
        description='Adiciona um novo signatário a um documento existente. O documento deve estar em rascunho ou pendente.',
        tags=['Documents'],
        request=AddSignerSerializer,
        responses={
            201: SignerSerializer,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        examples=[
            OpenApiExample(
                'Adicionar signatário',
                value={
                    'name': 'Carlos Oliveira',
                    'email': 'carlos@example.com'
                }
            ),
        ],
    )
    @action(detail=True, methods=['post'])
    def add_signer(self, request, company_pk=None, pk=None):
        document = self.get_object()
        serializer = AddSignerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = SignatureService()
            signer = service.add_signer_to_document(document, serializer.validated_data)
            return Response(SignerSerializer(signer).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response('Failed to add signer', status.HTTP_500_INTERNAL_SERVER_ERROR, {'detail': str(e)})

    @extend_schema(
        summary='Cancelar documento',
        description='Cancela um documento que está em processo de assinatura. O documento não poderá mais ser assinado após o cancelamento.',
        tags=['Documents'],
        responses={
            200: DocumentSerializer,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, company_pk=None, pk=None):
        document = self.get_object()
        try:
            service = SignatureService()
            document = service.cancel_document(document)
            return Response(DocumentSerializer(document).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return error_response('Failed to cancel document', status.HTTP_500_INTERNAL_SERVER_ERROR, {'detail': str(e)})

    @extend_schema(
        summary='Atualizar status do documento',
        description='Sincroniza o status do documento com o provedor de assinatura externo. Atualiza o status interno baseado no status atual no provedor.',
        tags=['Documents'],
        responses={
            200: DocumentSerializer,
            400: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
    )
    @action(detail=True, methods=['post'])
    def refresh_status(self, request, company_pk=None, pk=None):
        document = self.get_object()
        try:
            service = SignatureService()
            document = service.update_document_status(document)
            return Response(DocumentSerializer(document).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return error_response(str(e), status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Se o documento não foi encontrado no provider, retorna o documento atual
            if '404' in str(e) or 'not found' in str(e).lower() or 'not_found' in str(e):
                logger.warning(f'Document {document.id} not found in provider, returning current status')
                return Response(DocumentSerializer(document).data, status=status.HTTP_200_OK)
            return error_response('Failed to refresh document status', status.HTTP_500_INTERNAL_SERVER_ERROR, {'detail': str(e)})

    @extend_schema(
        summary='Obter alertas de documentos',
        description='Retorna uma lista de alertas relacionados aos documentos da empresa, como documentos próximos do vencimento ou com problemas.',
        tags=['Documents'],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'alerts': {
                        'type': 'array',
                        'description': 'Lista de alertas',
                    },
                    'count': {
                        'type': 'integer',
                        'description': 'Número total de alertas',
                    },
                },
            },
        },
    )
    @action(detail=False, methods=['get'])
    def alerts(self, request, company_pk=None):
        company = get_object_or_404(Company, pk=company_pk)
        alerts = get_document_alerts(company)
        return Response({'alerts': alerts, 'count': len(alerts)}, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Obter métricas de documentos',
        description='Retorna métricas agregadas sobre os documentos da empresa, como total de documentos, documentos assinados, pendentes, etc.',
        tags=['Documents'],
        responses={
            200: {
                'type': 'object',
                'description': 'Métricas agregadas dos documentos',
            },
        },
    )
    @action(detail=False, methods=['get'])
    def metrics(self, request, company_pk=None):
        company = get_object_or_404(Company, pk=company_pk)
        metrics = get_document_metrics(company)
        return Response(metrics, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(
        summary='Listar signatários do documento',
        description='Retorna uma lista de todos os signatários de um documento específico.',
        tags=['Signers'],
    ),
    retrieve=extend_schema(
        summary='Obter detalhes do signatário',
        description='Retorna os detalhes de um signatário específico, incluindo status e URL de assinatura.',
        tags=['Signers'],
    ),
)
class SignerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SignerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company_id = self.kwargs.get('company_pk')
        document_id = self.kwargs.get('document_pk')
        return Signer.objects.filter(document__company_id=company_id, document_id=document_id)

