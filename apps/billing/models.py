from django.db import models
from django.utils import timezone


class Payment(models.Model):
    class MethodChoices(models.TextChoices):
        CASH    = 'CASH',    'Cash'
        FONEPAY = 'FONEPAY', 'FonePay'
        ESEWA   = 'ESEWA',   'eSewa'
        KHALTI  = 'KHALTI',  'Khalti'
        CREDIT  = 'CREDIT',  'Credit'

    order   = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    method  = models.CharField(max_length=20, choices=MethodChoices.choices)
    amount  = models.DecimalField(max_digits=12, decimal_places=2)
    txn_ref = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-paid_at']

    def __str__(self):
        return f'{self.order} - {self.method} Rs.{self.amount}'


class CreditAccount(models.Model):
    name       = models.CharField(max_length=200, unique=True)
    phone      = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Refund(models.Model):
    payment     = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    reason      = models.CharField(max_length=255, blank=True)
    refunded_at = models.DateTimeField(default=timezone.now)
    notes       = models.TextField(blank=True)

    class Meta:
        ordering = ['-refunded_at']

    def __str__(self):
        return f'Refund Rs.{self.amount} — {self.payment}'


class CreditRecord(models.Model):
    class RecordType(models.TextChoices):
        CREDIT    = 'CREDIT',    'Credit'
        REPAYMENT = 'REPAYMENT', 'Repayment'

    account        = models.ForeignKey(CreditAccount, on_delete=models.PROTECT, related_name='records')
    record_type    = models.CharField(max_length=10, choices=RecordType.choices)
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    order          = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_records')
    payment_method = models.CharField(max_length=20, blank=True)
    notes          = models.CharField(max_length=500, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.record_type} Rs.{self.amount} - {self.account.name}'
