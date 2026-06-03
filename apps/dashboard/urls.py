from django.urls import path
from . import views

urlpatterns = [
    path('',           views.pos_view,       name='pos'),
    path('login/',     views.login_view,     name='login'),
    path('logout/',    views.logout_view,    name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # API endpoints
    path('api/tables/',                    views.api_tables,         name='api_tables'),
    path('api/categories/',                views.api_categories,     name='api_categories'),
    path('api/products/',                  views.api_products,       name='api_products'),
    path('api/orders/',                    views.api_orders,         name='api_orders'),
    path('api/orders/<int:order_id>/',     views.api_order_detail,   name='api_order_detail'),
    path('api/orders/<int:order_id>/add-item/',    views.api_add_item,      name='api_add_item'),
    path('api/orders/<int:order_id>/checkout/',    views.api_checkout,      name='api_checkout'),
    path('api/orders/<int:order_id>/cancel/',      views.api_cancel_order,  name='api_cancel_order'),
    path('api/dashboard/overview/',        views.api_dashboard,      name='api_dashboard'),
    path('api/dashboard/activity/',        views.api_activity,       name='api_activity'),
]
