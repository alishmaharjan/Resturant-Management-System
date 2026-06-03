from django.db import models
from django.utils import timezone


class Order(models.Model):
    class OrderTypeChoices(models.TextChoices):
        DINE_IN  = 'DINE_IN',  'Dine In'
        TAKEAWAY = 'TAKEAWAY', 'Takeaway'

    class StatusChoices(models.TextChoices):
        OPEN      = 'OPEN',      'Open'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        PREPARING = 'PREPARING', 'Preparing'
        SERVED    = 'SERVED',    'Served'
        PAID      = 'PAID',      'Paid'
        CANCELLED = 'CANCELLED', 'Cancelled'

    class PaymentStatusChoices(models.TextChoices):
        UNPAID  = 'UNPAID',  'Unpaid'
        PARTIAL = 'PARTIAL', 'Partial'
        PAID    = 'PAID',    'Paid'

    order_no       = models.CharField(max_length=30, unique=True, null=True, blank=True)
    order_type     = models.CharField(max_length=20, choices=OrderTypeChoices.choices, default=OrderTypeChoices.DINE_IN)
    table_no       = models.CharField(max_length=20, blank=True, null=True)
    status         = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.OPEN)
    subtotal       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount= models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PaymentStatusChoices.choices, default=PaymentStatusChoices.UNPAID)
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(default=timezone.now)
    updated_at     = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_no or f'Order #{self.pk}'


class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product    = models.ForeignKey('menu.MenuItem', on_delete=models.PROTECT, related_name='order_items')
    qty        = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.line_total = self.qty * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.order} - {self.product.name} x {self.qty}'
