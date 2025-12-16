import re
import requests
from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from apps.domain.models import Provider, Company, Document, Signer, DocumentAnalysis
from apps.application.services.signature_service import SignatureService
from apps.application.services.document_analysis_service import DocumentAnalysisService


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ['id', 'name', 'code', 'api_base_url', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanySerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    provider_code = serializers.CharField(source='provider.code', read_only=True)

    class Meta:
        model = Company
        fields = ['id', 'name', 'provider', 'provider_name', 'provider_code', 'api_token', 'provider_config', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SignerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signer
        fields = [
            'id', 'name', 'email', 'status',
            'token', 'sign_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'token', 'sign_url', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    signers = SignerSerializer(many=True, read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'company', 'company_name', 'name', 'open_id', 'token',
            'provider_status', 'internal_status', 'file_url', 'date_limit_to_sign',
            'created_by', 'signers', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'open_id', 'token', 'provider_status', 'internal_status', 'created_at', 'updated_at']


class DocumentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    url_pdf = serializers.URLField()
    signers = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    date_limit_to_sign = serializers.DateTimeField(required=False)

    def validate_url_pdf(self, value):
        validator = URLValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError('Invalid URL format')
        
        if not value.lower().endswith('.pdf'):
            raise serializers.ValidationError('URL must point to a PDF file')
        
        try:
            response = requests.head(value, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    try:
                        file_size_mb = int(content_length) / (1024 * 1024)
                        if file_size_mb > 10:
                            raise serializers.ValidationError(f'PDF file size ({file_size_mb:.2f}MB) exceeds maximum limit of 10MB')
                    except (ValueError, TypeError):
                        pass
        except requests.RequestException:
            pass
        
        return value

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
        
        service = SignatureService()
        return service.create_document(
            company=company,
            created_by=created_by,
            **validated_data,
            signers_data=signers_data
        )


class DocumentAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentAnalysis
        fields = ['id', 'document', 'missing_topics', 'summary', 'insights', 'analyzed_at', 'model_used']
        read_only_fields = ['id', 'analyzed_at']


class AddSignerSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()

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


