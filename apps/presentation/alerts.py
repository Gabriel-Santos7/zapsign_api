from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.domain.models import Document, Company


def get_document_alerts(company: Company):
    alerts = []
    documents = Document.objects.filter(company=company)
    
    for document in documents:
        alert = None
        
        # Documento expirado (data limite passou)
        if document.internal_status == 'pending' and document.date_limit_to_sign:
            if timezone.now() > document.date_limit_to_sign:
                alert = {
                    'id': document.id,  # Adicionar id para compatibilidade
                    'document_id': document.id,
                    'document_name': document.name,
                    'type': 'expired',
                    'message': f'Documento "{document.name}" expirou e precisa de atenção',
                    'severity': 'error',  # Mudar para 'error' para compatibilidade com frontend
                    'created_at': document.date_limit_to_sign.isoformat()
                }
        
        # Documento pendente há muito tempo (sem data limite)
        if document.internal_status == 'pending' and not document.date_limit_to_sign:
            days_since_creation = (timezone.now() - document.created_at).days
            if days_since_creation >= 7:
                alert = {
                    'id': document.id,
                    'document_id': document.id,
                    'document_name': document.name,
                    'type': 'pending_too_long',
                    'message': f'Documento "{document.name}" está pendente há {days_since_creation} dias',
                    'severity': 'warning',  # Mudar para 'warning' para compatibilidade
                    'created_at': document.created_at.isoformat()
                }
        
        # Documento em progresso há muito tempo sem atualização
        if document.internal_status == 'in_progress':
            days_since_update = (timezone.now() - document.updated_at).days
            if days_since_update >= 3:
                alert = {
                    'id': document.id,
                    'document_id': document.id,
                    'document_name': document.name,
                    'type': 'stagnated',
                    'message': f'Documento "{document.name}" está em progresso há {days_since_update} dias sem atualizações',
                    'severity': 'warning',
                    'created_at': document.updated_at.isoformat()
                }
        
        # Documento próximo do vencimento (3 dias antes)
        if document.internal_status == 'pending' and document.date_limit_to_sign:
            days_until_expiry = (document.date_limit_to_sign - timezone.now()).days
            if 0 <= days_until_expiry <= 3:
                alert = {
                    'id': document.id,
                    'document_id': document.id,
                    'document_name': document.name,
                    'type': 'expiring_soon',
                    'message': f'Documento "{document.name}" expira em {days_until_expiry} dia(s)',
                    'severity': 'warning',
                    'created_at': document.date_limit_to_sign.isoformat()
                }
        
        if alert:
            alerts.append(alert)
    
    # Ordenar por severidade (error > warning > info) e depois por data
    severity_order = {'error': 0, 'warning': 1, 'info': 2}
    alerts.sort(key=lambda x: (severity_order.get(x.get('severity', 'info'), 2), x.get('created_at', '')))
    
    return alerts


def get_document_metrics(company: Company):
    documents = Document.objects.filter(company=company)
    total = documents.count()
    
    status_counts = {}
    for status_choice in Document.STATUS_CHOICES:
        status_counts[status_choice[0]] = documents.filter(internal_status=status_choice[0]).count()
    
    signed_count = status_counts.get('signed', 0)
    signature_rate = (signed_count / total * 100) if total > 0 else 0
    
    signed_documents = documents.filter(internal_status='signed')
    avg_signature_time = None
    if signed_documents.exists():
        times = []
        for doc in signed_documents:
            if doc.created_at and doc.updated_at:
                delta = doc.updated_at - doc.created_at
                times.append(delta.total_seconds() / 3600)
        if times:
            avg_signature_time = sum(times) / len(times)
    
    expiring_soon = documents.filter(
        internal_status='pending',
        date_limit_to_sign__lte=timezone.now() + timedelta(days=3),
        date_limit_to_sign__gte=timezone.now()
    ).count()
    
    return {
        'total_documents': total,
        'status_breakdown': status_counts,
        'signature_rate': round(signature_rate, 2),
        'average_signature_time_hours': round(avg_signature_time, 2) if avg_signature_time else None,
        'expiring_soon_count': expiring_soon,
    }


