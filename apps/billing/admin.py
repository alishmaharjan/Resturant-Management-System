from django.contrib import admin
from .models import Payment, CreditAccount, CreditRecord, Refund

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'method', 'amount', 'paid_at')
    list_filter  = ('method',)

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display  = ('payment', 'amount', 'reason', 'refunded_at')
    list_filter   = ('refunded_at',)
    raw_id_fields = ('payment',)

@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'created_at')

@admin.register(CreditRecord)
class CreditRecordAdmin(admin.ModelAdmin):
    list_display = ('account', 'record_type', 'amount', 'created_at')
