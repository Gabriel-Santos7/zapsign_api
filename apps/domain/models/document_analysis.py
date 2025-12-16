from django.db import models
from .document import Document


class DocumentAnalysis(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='analysis')
    missing_topics = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    insights = models.JSONField(default=dict, blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)
    model_used = models.CharField(max_length=100, default='gpt-3.5-turbo')

    class Meta:
        db_table = 'document_analyses'
        verbose_name_plural = 'document analyses'

    def __str__(self):
        return f"Analysis for {self.document.name}"


