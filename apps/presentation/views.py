from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from apps.domain.models import Provider, Company, Document, Signer, DocumentAnalysis
from apps.presentation.serializers import (
    ProviderSerializer, CompanySerializer, DocumentSerializer,
    DocumentCreateSerializer, SignerSerializer, DocumentAnalysisSerializer,
    AddSignerSerializer
)
from apps.application.services.signature_service import SignatureService
from apps.application.services.document_analysis_service import DocumentAnalysisService
from apps.presentation.alerts import get_document_alerts, get_document_metrics


class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Provider.objects.filter(is_active=True)
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Company.objects.all()


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

    @action(detail=True, methods=['post'])
    def analyze(self, request, company_pk=None, pk=None):
        document = self.get_object()
        try:
            service = DocumentAnalysisService()
            analysis = service.analyze_document(document)
            return Response(DocumentAnalysisSerializer(analysis).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def insights(self, request, company_pk=None, pk=None):
        document = self.get_object()
        try:
            analysis = document.analysis
            return Response(DocumentAnalysisSerializer(analysis).data, status=status.HTTP_200_OK)
        except DocumentAnalysis.DoesNotExist:
            return Response({'error': 'Document has not been analyzed yet'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def add_signer(self, request, company_pk=None, pk=None):
        document = self.get_object()
        serializer = AddSignerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            service = SignatureService()
            signer = service.add_signer_to_document(document, serializer.validated_data)
            return Response(SignerSerializer(signer).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, company_pk=None, pk=None):
        document = self.get_object()
        try:
            service = SignatureService()
            document = service.cancel_document(document)
            return Response(DocumentSerializer(document).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def refresh_status(self, request, company_pk=None, pk=None):
        document = self.get_object()
        try:
            service = SignatureService()
            document = service.update_document_status(document)
            return Response(DocumentSerializer(document).data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def alerts(self, request, company_pk=None):
        company = get_object_or_404(Company, pk=company_pk)
        alerts = get_document_alerts(company)
        return Response({'alerts': alerts, 'count': len(alerts)}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def metrics(self, request, company_pk=None):
        company = get_object_or_404(Company, pk=company_pk)
        metrics = get_document_metrics(company)
        return Response(metrics, status=status.HTTP_200_OK)


class SignerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SignerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        company_id = self.kwargs.get('company_pk')
        document_id = self.kwargs.get('document_pk')
        return Signer.objects.filter(document__company_id=company_id, document_id=document_id)

