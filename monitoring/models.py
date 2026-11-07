from django.db import models


class QueryLog(models.Model):
    """One assistant question. The question text is deliberately not stored:
    chat stays anonymous and history-free (see README)."""
    PAGE, POPUP = 'page', 'popup'
    CHANNELS = [(PAGE, 'Full-page chat'), (POPUP, 'Popup')]

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    channel = models.CharField(max_length=10, choices=CHANNELS)
    latency_ms = models.PositiveIntegerField()
    succeeded = models.BooleanField()
    source_count = models.PositiveSmallIntegerField(default=0)
    error_type = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-created_at', '-pk']

    @property
    def answered(self):
        return self.succeeded and self.source_count > 0

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.channel} {self.latency_ms} ms'
