from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.menu_list,       name='menu_list'),
    path('category/add/',             views.category_add,    name='category_add'),
    path('category/<int:pk>/edit/',   views.category_edit,   name='category_edit'),
    path('category/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('category/<int:pk>/toggle/', views.category_toggle, name='category_toggle'),
    path('item/add/',                 views.item_add,        name='item_add'),
    path('item/<int:pk>/edit/',       views.item_edit,       name='item_edit'),
    path('item/<int:pk>/delete/',     views.item_delete,     name='item_delete'),
    path('item/<int:pk>/toggle/',     views.item_toggle,     name='item_toggle'),
]
