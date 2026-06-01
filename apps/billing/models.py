from django.db import models
from apps.orders.models import Order

class Invoice(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH   = 'cash',   'Cash'
        CARD   = 'card',   'Card'
        ESEWA  = 'esewa',  'eSewa'
        KHALTI = 'khalti', 'Khalti'

    class Status(models.TextChoices):
        UNPAID = 'unpaid', 'Unpaid'
        PAID   = 'paid',   'Paid'

    order          = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    status         = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)
    discount       = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_percent    = models.DecimalField(max_digits=4, decimal_places=2, default=13)  # 13% VAT Nepal
    created_at     = models.DateTimeField(auto_now_add=True)
    paid_at        = models.DateTimeField(null=True, blank=True)

    def get_subtotal(self):
        return self.order.get_total()

    def get_tax_amount(self):
        return self.get_subtotal() * (self.tax_percent / 100)

    def get_grand_total(self):
        return self.get_subtotal() + self.get_tax_amount() - self.discount

    def __str__(self):
        return f"Invoice #{self.id} - Order #{self.order.id} [{self.status}]"
