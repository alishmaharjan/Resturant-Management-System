from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_no', 'order_type', 'table_no', 'status', 'grand_total', 'created_at')
    list_filter  = ('status', 'order_type')
    inlines      = [OrderItemInline]
