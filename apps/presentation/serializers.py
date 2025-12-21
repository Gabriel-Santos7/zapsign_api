import re
import requests
from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_field
from apps.domain.models import Provider, Company, Document, Signer, DocumentAnalysis
from apps.application.services.signature_service import SignatureService
from apps.application.services.document_analysis_service import DocumentAnalysisService


class ProviderSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text='ID único do provedor')
    name = serializers.CharField(help_text='Nome do provedor de assinatura digital')
    code = serializers.SlugField(help_text='Código único do provedor (slug)')
    api_base_url = serializers.URLField(help_text='URL base da API do provedor')
    is_active = serializers.BooleanField(help_text='Indica se o provedor está ativo')
    created_at = serializers.DateTimeField(read_only=True, help_text='Data de criação')
    updated_at = serializers.DateTimeField(read_only=True, help_text='Data da última atualização')

    class Meta:
        model = Provider
        fields = ['id', 'name', 'code', 'api_base_url', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text='ID único da empresa')
    name = serializers.CharField(help_text='Nome da empresa')
    provider = serializers.PrimaryKeyRelatedField(
        queryset=Provider.objects.filter(is_active=True),
        help_text='ID do provedor de assinatura digital associado'
    )
    provider_name = serializers.CharField(source='provider.name', read_only=True, help_text='Nome do provedor (somente leitura)')
    provider_code = serializers.CharField(source='provider.code', read_only=True, help_text='Código do provedor (somente leitura)')
    api_token = serializers.CharField(help_text='Token de autenticação da API do provedor')
    provider_config = serializers.JSONField(
        default=dict,
        help_text='Configurações adicionais do provedor em formato JSON'
    )
    created_at = serializers.DateTimeField(read_only=True, help_text='Data de criação')
    updated_at = serializers.DateTimeField(read_only=True, help_text='Data da última atualização')

    class Meta:
        model = Company
        fields = ['id', 'name', 'provider', 'provider_name', 'provider_code', 'api_token', 'provider_config', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SignerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text='ID único do signatário')
    name = serializers.CharField(help_text='Nome completo do signatário')
    email = serializers.EmailField(help_text='E-mail do signatário')
    status = serializers.ChoiceField(
        choices=Signer.STATUS_CHOICES,
        read_only=True,
        help_text='Status do signatário: pending, in_progress, signed, rejected, cancelled'
    )
    token = serializers.CharField(read_only=True, help_text='Token único do signatário para acesso ao documento')
    sign_url = serializers.URLField(read_only=True, help_text='URL para assinatura do documento')
    created_at = serializers.DateTimeField(read_only=True, help_text='Data de criação')
    updated_at = serializers.DateTimeField(read_only=True, help_text='Data da última atualização')

    class Meta:
        model = Signer
        fields = [
            'id', 'name', 'email', 'status',
            'token', 'sign_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'token', 'sign_url', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text='ID único do documento')
    company = serializers.PrimaryKeyRelatedField(read_only=True, help_text='ID da empresa proprietária')
    company_name = serializers.CharField(source='company.name', read_only=True, help_text='Nome da empresa (somente leitura)')
    name = serializers.CharField(help_text='Nome do documento')
    open_id = serializers.CharField(read_only=True, help_text='ID externo do documento no provedor')
    token = serializers.CharField(read_only=True, help_text='Token único do documento')
    provider_status = serializers.CharField(read_only=True, help_text='Status do documento no provedor externo')
    internal_status = serializers.ChoiceField(
        choices=Document.STATUS_CHOICES,
        read_only=True,
        help_text='Status interno: draft, pending, in_progress, signed, cancelled, rejected, expired'
    )
    file_url = serializers.URLField(help_text='URL do arquivo PDF do documento')
    date_limit_to_sign = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='Data limite para assinatura do documento (opcional)'
    )
    created_by = serializers.PrimaryKeyRelatedField(read_only=True, help_text='ID do usuário que criou o documento')
    signers = SignerSerializer(many=True, read_only=True, help_text='Lista de signatários do documento')
    created_at = serializers.DateTimeField(read_only=True, help_text='Data de criação')
    updated_at = serializers.DateTimeField(read_only=True, help_text='Data da última atualização')

    class Meta:
        model = Document
        fields = [
            'id', 'company', 'company_name', 'name', 'open_id', 'token',
            'provider_status', 'internal_status', 'file_url', 'date_limit_to_sign',
            'created_by', 'signers', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'open_id', 'token', 'provider_status', 'internal_status', 'created_at', 'updated_at']


class DocumentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        help_text='Nome do documento (máximo 255 caracteres)'
    )
    url_pdf = serializers.URLField(
        help_text='URL do arquivo PDF. Deve ser uma URL válida apontando para um arquivo .pdf acessível'
    )
    signers = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text='Lista de signatários. Cada signatário deve ter "name" e "email". Mínimo de 1 signatário.'
    )
    date_limit_to_sign = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='Data limite para assinatura do documento (opcional, formato ISO 8601)'
    )
    save_as_draft = serializers.BooleanField(
        default=False,
        required=False,
        help_text='Se True, salva o documento como rascunho sem validar o acesso ao PDF'
    )

    def validate_url_pdf(self, value):
        validator = URLValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError('Invalid URL format')
        
        if not value.lower().endswith('.pdf'):
            raise serializers.ValidationError('URL must point to a PDF file')
        
        return value
    
    def validate(self, data):
        # Se não for rascunho, valida acesso ao PDF
        if not data.get('save_as_draft', False):
            url_pdf = data.get('url_pdf')
            if url_pdf:
                try:
                    response = requests.head(url_pdf, timeout=10, allow_redirects=True)
                    if response.status_code == 200:
                        content_length = response.headers.get('Content-Length')
                        if content_length:
                            try:
                                file_size_mb = int(content_length) / (1024 * 1024)
                                if file_size_mb > 10:
                                    raise serializers.ValidationError({
                                        'url_pdf': f'PDF file size ({file_size_mb:.2f}MB) exceeds maximum limit of 10MB'
                                    })
                            except (ValueError, TypeError):
                                pass
                except requests.RequestException:
                    # Para rascunhos, não valida acesso HTTP
                    pass
        return data

    def validate_signers(self, value):
        if not value:
            raise serializers.ValidationError('At least one signer is required')
        
        for signer in value:
            if not signer.get('name'):
                raise serializers.ValidationError('Signer name is required')
            
            if not signer.get('email'):
                raise serializers.ValidationError('Signer email is required')
            
            email = signer.get('email', '')
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise serializers.ValidationError(f'Invalid email format: {email}')
        
        return value
    

    def create(self, validated_data):
        company = self.context['company']
        created_by = self.context.get('user')
        signers_data = validated_data.pop('signers')
        save_as_draft = validated_data.pop('save_as_draft', False)
        
        service = SignatureService()
        return service.create_document(
            company=company,
            created_by=created_by,
            save_as_draft=save_as_draft,
            **validated_data,
            signers_data=signers_data
        )


class DocumentAnalysisSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True, help_text='ID único da análise')
    document = serializers.PrimaryKeyRelatedField(read_only=True, help_text='ID do documento analisado')
    missing_topics = serializers.JSONField(
        default=list,
        help_text='Lista de tópicos que podem estar faltando no documento (JSON array)'
    )
    summary = serializers.CharField(
        allow_blank=True,
        help_text='Resumo da análise do documento gerado por IA'
    )
    insights = serializers.JSONField(
        default=dict,
        help_text='Insights e informações adicionais sobre o documento (JSON object)'
    )
    analyzed_at = serializers.DateTimeField(read_only=True, help_text='Data e hora em que a análise foi realizada')
    model_used = serializers.CharField(
        default='spacy',
        help_text='Modelo de IA utilizado para análise (ex: spacy, gemini)'
    )
    analysis_metadata = serializers.JSONField(
        default=dict,
        help_text='Metadados adicionais da análise (JSON object)'
    )

    class Meta:
        model = DocumentAnalysis
        fields = ['id', 'document', 'missing_topics', 'summary', 'insights', 'analyzed_at', 'model_used', 'analysis_metadata']
        read_only_fields = ['id', 'analyzed_at']


class AddSignerSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=200,
        help_text='Nome completo do signatário (máximo 200 caracteres)'
    )
    email = serializers.EmailField(
        help_text='E-mail válido do signatário'
    )

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Signer name is required and cannot be empty')
        return value.strip()

    def validate_email(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Signer email is required and cannot be empty')
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise serializers.ValidationError('Invalid email format')
        
        return value.strip()


