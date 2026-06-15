from django.urls import path
from . import views

urlpatterns = [
    path('',                                  views.billing_list,              name='billing_list'),
    path('payments/<int:pk>/refund/',         views.refund_payment,            name='refund_payment'),
    path('credits/',                          views.credit_list,               name='credit_list'),
    path('credits/export/',                   views.export_credit_summary_csv, name='export_credit_summary'),
    path('credits/<int:pk>/',                 views.credit_detail,             name='credit_detail'),
    path('credits/<int:pk>/repay/',           views.credit_repay,              name='credit_repay'),
    path('credits/<int:pk>/export/',          views.export_credit_detail_csv,  name='export_credit_detail'),
]
