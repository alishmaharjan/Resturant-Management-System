from django.db import models

class Category(models.Model):
    name      = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category     = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='items')
    name         = models.CharField(max_length=200)
    description  = models.TextField(blank=True)
    price        = models.DecimalField(max_digits=8, decimal_places=2)
    image        = models.ImageField(upload_to='menu/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - Rs.{self.price}"
