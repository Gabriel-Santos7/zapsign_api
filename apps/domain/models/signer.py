from django.db import models
from .document import Document


class Signer(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('signed', 'Signed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signers')
    name = models.CharField(max_length=200)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    token = models.CharField(max_length=255, blank=True, null=True)
    sign_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'signers'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.status}"

