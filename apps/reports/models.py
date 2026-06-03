from django.db import models


class AuditLog(models.Model):
    class EventTypeChoices(models.TextChoices):
        ORDER     = 'ORDER',     'Order'
        PAYMENT   = 'PAYMENT',   'Payment'
        SHIFT     = 'SHIFT',     'Shift'
        REPORT    = 'REPORT',    'Report'

    event_type   = models.CharField(max_length=20, choices=EventTypeChoices.choices)
    action       = models.CharField(max_length=80)
    message      = models.CharField(max_length=255)
    reference_id = models.CharField(max_length=80, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} / {self.action}'
