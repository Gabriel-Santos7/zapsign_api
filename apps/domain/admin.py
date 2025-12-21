from django.contrib import admin
from .models import Provider, Company, Document, Signer, DocumentAnalysis


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'api_base_url', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'api_token', 'created_at']
    list_filter = ['provider', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'provider')
        }),
        ('Configuração ZapSign', {
            'fields': ('api_token', 'provider_config')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'internal_status', 'provider_status', 'created_at']
    list_filter = ['internal_status', 'provider_status', 'created_at', 'company']
    search_fields = ['name', 'token', 'open_id']
    readonly_fields = ['open_id', 'token', 'provider_status', 'internal_status', 'created_at', 'updated_at']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'company', 'file_url', 'created_by')
        }),
        ('Status', {
            'fields': ('internal_status', 'provider_status', 'open_id', 'token')
        }),
        ('Configurações', {
            'fields': ('date_limit_to_sign',)
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Signer)
class SignerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'document', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email', 'token']
    readonly_fields = ['token', 'sign_url', 'status', 'created_at', 'updated_at']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('document', 'name', 'email')
        }),
        ('Status e Tokens', {
            'fields': ('status', 'token', 'sign_url')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DocumentAnalysis)
class DocumentAnalysisAdmin(admin.ModelAdmin):
    list_display = ['document', 'model_used', 'analyzed_at']
    list_filter = ['model_used', 'analyzed_at']
    search_fields = ['document__name', 'summary']
    readonly_fields = ['analyzed_at']
    fieldsets = (
        ('Documento', {
            'fields': ('document',)
        }),
        ('Análise', {
            'fields': ('summary', 'missing_topics', 'insights', 'model_used', 'analyzed_at')
        }),
    )


