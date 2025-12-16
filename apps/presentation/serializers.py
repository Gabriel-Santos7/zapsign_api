from rest_framework import serializers
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


