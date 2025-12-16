from django.db import models
from django.contrib.auth.models import User
from .company import Company


class Document(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('signed', 'Signed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=255)
    open_id = models.CharField(max_length=255, blank=True, null=True)
    token = models.CharField(max_length=255, blank=True, null=True)
    provider_status = models.CharField(max_length=50, blank=True, null=True)
    internal_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    file_url = models.URLField()
    date_limit_to_sign = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.internal_status})"


