from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from apps.orders.models import Order, OrderItem
from apps.billing.models import Payment
from apps.reports.models import AuditLog
import json


@login_required(login_url='/login/')
def reports_index(request):
    today    = timezone.now().date()
    tz       = timezone.get_current_timezone()

    # Date range selector
    range_opt = request.GET.get('range', 'today')
    if range_opt == 'week':
        from datetime import timedelta
        date_from = today - timedelta(days=6)
    elif range_opt == 'month':
        date_from = today.replace(day=1)
    else:
        date_from = today

    start = timezone.datetime.combine(date_from, timezone.datetime.min.time()).replace(tzinfo=tz)
    end   = timezone.datetime.combine(today,     timezone.datetime.max.time()).replace(tzinfo=tz)

    paid_orders = Order.objects.filter(status='PAID', created_at__gte=start, created_at__lte=end)
    agg         = paid_orders.aggregate(revenue=Sum('grand_total'), count=Count('id'))
    revenue     = agg['revenue'] or 0
    order_count = agg['count']   or 0
    avg_order   = (revenue / order_count) if order_count else 0

    # Top selling items
    top_items = (
        OrderItem.objects
        .filter(order__status='PAID', order__created_at__gte=start)
        .values('product__name', 'product__category__name')
        .annotate(qty=Sum('qty'), revenue=Sum('line_total'))
        .order_by('-revenue')[:12]
    )

    # Payment breakdown
    pay_breakdown = (
        Payment.objects
        .filter(paid_at__gte=start, paid_at__lte=end)
        .values('method')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )

    # Last 7 days revenue for chart
    from datetime import timedelta
    chart_labels, chart_data = [], []
    for i in range(6, -1, -1):
        d  = today - timedelta(days=i)
        ds = timezone.datetime.combine(d, timezone.datetime.min.time()).replace(tzinfo=tz)
        de = timezone.datetime.combine(d, timezone.datetime.max.time()).replace(tzinfo=tz)
        rev = Order.objects.filter(
            status='PAID', created_at__gte=ds, created_at__lte=de
        ).aggregate(t=Sum('grand_total'))['t'] or 0
        chart_labels.append(d.strftime('%d %b'))
        chart_data.append(float(rev))

    # Audit log
    audit_logs = AuditLog.objects.all()[:50]

    return render(request, 'reports/index.html', {
        'range_opt':     range_opt,
        'date_from':     date_from,
        'today':         today,
        'revenue':       revenue,
        'order_count':   order_count,
        'avg_order':     avg_order,
        'top_items':     top_items,
        'pay_breakdown': pay_breakdown,
        'chart_labels':  json.dumps(chart_labels),
        'chart_data':    json.dumps(chart_data),
        'audit_logs':    audit_logs,
    })
