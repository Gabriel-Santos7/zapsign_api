from django.db import models
from .provider import Provider


class Company(models.Model):
    name = models.CharField(max_length=200)
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT, related_name='companies')
    api_token = models.CharField(max_length=500)
    provider_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'companies'
        ordering = ['name']
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name


