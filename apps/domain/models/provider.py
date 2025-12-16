from django.db import models


class Provider(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50, unique=True)
    api_base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'providers'
        ordering = ['name']

    def __str__(self):
        return self.name


