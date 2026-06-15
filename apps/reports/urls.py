from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.reports_index,          name='reports_index'),
    path('export/sales/',       views.export_sales_csv,       name='export_sales'),
    path('export/items/',       views.export_order_items_csv, name='export_items'),
    path('export/products/',    views.export_products_csv,    name='export_products'),
    path('export/payments/',    views.export_payments_csv,    name='export_payments'),
    path('export/master/',      views.export_master_report,   name='export_master'),
]
