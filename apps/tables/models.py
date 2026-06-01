from django.db import models

class Table(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        OCCUPIED  = 'occupied',  'Occupied'
        RESERVED  = 'reserved',  'Reserved'

    number   = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField(default=4)
    status   = models.CharField(max_length=10, choices=Status.choices, default=Status.AVAILABLE)

    def __str__(self):
        return f"Table {self.number} ({self.get_status_display()})"
