from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.svg', permanent=True)),
    path('admin/', admin.site.urls),
    path('',        include('apps.dashboard.urls')),
    path('tables/', include('apps.tables.urls')),
    path('menu/',   include('apps.menu.urls')),
    path('orders/', include('apps.orders.urls')),
    path('billing/',  include('apps.billing.urls')),
    path('reports/',  include('apps.reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
