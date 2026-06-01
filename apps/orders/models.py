from django.db import models
from apps.tables.models import Table
from apps.menu.models import MenuItem

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        PREPARING = 'preparing', 'Preparing'
        SERVED    = 'served',    'Served'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    table      = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, related_name='orders')
    status     = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    note       = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())

    def __str__(self):
        return f"Order #{self.id} - Table {self.table} [{self.status}]"


class OrderItem(models.Model):
    order     = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True)
    quantity  = models.PositiveIntegerField(default=1)
    price     = models.DecimalField(max_digits=8, decimal_places=2)

    def get_subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.menu_item} (Order #{self.order.id})"
