from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.table_list,   name='table_list'),
    path('add/',                    views.table_add,    name='table_add'),
    path('<int:pk>/edit/',          views.table_edit,   name='table_edit'),
    path('<int:pk>/delete/',        views.table_delete, name='table_delete'),
    path('<int:pk>/toggle/',        views.table_toggle, name='table_toggle'),
]
