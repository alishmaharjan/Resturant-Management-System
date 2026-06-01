from django.contrib import admin
from .models import Invoice

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'payment_method', 'status', 'get_grand_total', 'created_at')
    list_filter  = ('status', 'payment_method')
