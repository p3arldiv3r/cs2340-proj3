from django.db import models

class Source(models.Model):
    method = models.CharField(max_length=20)
    location = models.CharField(max_length=2048)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['method', 'location'], name='unique_source')]
    def __str__(self):
        return self.location

class Document(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='documents')
    external_id = models.CharField(max_length=2048)
    title = models.CharField(max_length=500)
    text = models.TextField()
    metadata = models.JSONField(default=dict)
    content_hash = models.CharField(max_length=64)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['source', 'external_id'], name='unique_source_record')]
    @property
    def public_url(self):
        from urllib.parse import urlsplit
        candidate = str(self.metadata.get('url', '') or (self.source.location if self.source.method == 'web' else ''))
        try:
            parsed = urlsplit(candidate)
        except ValueError:
            return ''
        return candidate if parsed.scheme in ('http', 'https') and parsed.netloc else ''
    def __str__(self):
        return self.title

class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    position = models.PositiveIntegerField()
    text = models.TextField()
    class Meta:
        ordering = ['document_id', 'position']
        constraints = [models.UniqueConstraint(fields=['document', 'position'], name='unique_chunk_position')]
