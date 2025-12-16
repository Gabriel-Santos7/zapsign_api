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
        
        if document.internal_status == 'pending' and document.date_limit_to_sign:
            if timezone.now() > document.date_limit_to_sign:
                alert = {
                    'document_id': document.id,
                    'document_name': document.name,
                    'type': 'expired',
                    'message': f'Document "{document.name}" has expired',
                    'severity': 'high',
                    'created_at': document.date_limit_to_sign.isoformat()
                }
        
        if document.internal_status == 'pending' and not document.date_limit_to_sign:
            days_since_creation = (timezone.now() - document.created_at).days
            if days_since_creation >= 7:
                alert = {
                    'document_id': document.id,
                    'document_name': document.name,
                    'type': 'pending_too_long',
                    'message': f'Document "{document.name}" has been pending for {days_since_creation} days',
                    'severity': 'medium',
                    'created_at': document.created_at.isoformat()
                }
        
        if document.internal_status == 'in_progress':
            days_since_update = (timezone.now() - document.updated_at).days
            if days_since_update >= 3:
                alert = {
                    'document_id': document.id,
                    'document_name': document.name,
                    'type': 'stagnated',
                    'message': f'Document "{document.name}" has been in progress for {days_since_update} days without updates',
                    'severity': 'medium',
                    'created_at': document.updated_at.isoformat()
                }
        
        if alert:
            alerts.append(alert)
    
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


