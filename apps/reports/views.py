import csv
import json
from datetime import timedelta
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Prefetch
from django.utils import timezone
from apps.orders.models import Order, OrderItem
from apps.billing.models import Payment
from apps.reports.models import AuditLog


def _date_range(request, default_range='today'):
    """Parse start/end datetimes from request GET params or range preset."""
    today = timezone.now().date()
    tz    = timezone.get_current_timezone()

    range_opt  = request.GET.get('range', default_range)
    date_from  = request.GET.get('date_from', '')
    date_to    = request.GET.get('date_to', '')

    if date_from and date_to:
        try:
            from datetime import date
            date_from = date.fromisoformat(date_from)
            date_to   = date.fromisoformat(date_to)
            range_opt = 'custom'
        except ValueError:
            date_from = date_to = today
            range_opt = default_range
    elif range_opt == 'week':
        date_from = today - timedelta(days=6)
        date_to   = today
    elif range_opt == 'month':
        date_from = today.replace(day=1)
        date_to   = today
    else:
        date_from = date_to = today

    start = timezone.datetime.combine(date_from, timezone.datetime.min.time()).replace(tzinfo=tz)
    end   = timezone.datetime.combine(date_to,   timezone.datetime.max.time()).replace(tzinfo=tz)
    return date_from, date_to, start, end, range_opt


@login_required(login_url='/login/')
def reports_index(request):
    date_from, date_to, start, end, range_opt = _date_range(request)

    paid_orders = Order.objects.filter(status='PAID', created_at__gte=start, created_at__lte=end)
    agg         = paid_orders.aggregate(revenue=Sum('grand_total'), count=Count('id'))
    revenue     = agg['revenue'] or 0
    order_count = agg['count']   or 0
    avg_order   = (revenue / order_count) if order_count else 0

    top_items = (
        OrderItem.objects
        .filter(order__status='PAID', order__created_at__gte=start)
        .values('product__name', 'product__category__name')
        .annotate(qty=Sum('qty'), revenue=Sum('line_total'))
        .order_by('-revenue')[:15]
    )

    pay_breakdown = (
        Payment.objects
        .filter(paid_at__gte=start, paid_at__lte=end)
        .values('method')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )

    # Last 7 days for chart
    chart_labels, chart_data = [], []
    for i in range(6, -1, -1):
        d   = date_to - timedelta(days=i)
        tz  = timezone.get_current_timezone()
        ds  = timezone.datetime.combine(d, timezone.datetime.min.time()).replace(tzinfo=tz)
        de  = timezone.datetime.combine(d, timezone.datetime.max.time()).replace(tzinfo=tz)
        rev = Order.objects.filter(
            status='PAID', created_at__gte=ds, created_at__lte=de
        ).aggregate(t=Sum('grand_total'))['t'] or 0
        chart_labels.append(d.strftime('%d %b'))
        chart_data.append(float(rev))

    audit_logs = AuditLog.objects.all()[:50]

    return render(request, 'reports/index.html', {
        'range_opt':    range_opt,
        'date_from':    date_from,
        'date_to':      date_to,
        'revenue':      revenue,
        'order_count':  order_count,
        'avg_order':    avg_order,
        'top_items':    top_items,
        'pay_breakdown': pay_breakdown,
        'chart_labels': json.dumps(chart_labels),
        'chart_data':   json.dumps(chart_data),
        'audit_logs':   audit_logs,
    })


# ── CSV Exports ────────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def export_sales_csv(request):
    """Download sales report: one row per paid order."""
    date_from, date_to, start, end, _ = _date_range(request)
    orders = (
        Order.objects
        .filter(status='PAID', created_at__gte=start, created_at__lte=end)
        .prefetch_related('payments', 'credit_records__account', 'items')
        .annotate(item_count=Count('items'))
        .order_by('created_at')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="yasumi_sales_{date_from}_{date_to}.csv"'
    )
    w = csv.writer(response)
    w.writerow(['Order No', 'Date', 'Time', 'Type', 'Table', 'Items',
                'Subtotal', 'Discount', 'Grand Total', 'Payment Methods'])
    for o in orders:
        methods = []
        for p in o.payments.all():
            methods.append(p.method)
        for cr in o.credit_records.all():
            methods.append(f'CREDIT ({cr.account.name})')
        w.writerow([
            o.order_no,
            o.created_at.strftime('%Y-%m-%d'),
            o.created_at.strftime('%H:%M'),
            o.order_type,
            o.table_no or '—',
            o.item_count,
            o.subtotal,
            o.discount_amount,
            o.grand_total,
            ', '.join(methods) or '—',
        ])
    return response


@login_required(login_url='/login/')
def export_order_items_csv(request):
    """Download detailed order items: one row per item in each paid order."""
    date_from, date_to, start, end, _ = _date_range(request)
    items = (
        OrderItem.objects
        .filter(order__status='PAID', order__created_at__gte=start, order__created_at__lte=end)
        .select_related('order', 'product', 'product__category')
        .order_by('order__created_at', 'id')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="yasumi_order_items_{date_from}_{date_to}.csv"'
    )
    w = csv.writer(response)
    w.writerow(['Order No', 'Date', 'Type', 'Table',
                'Category', 'Item', 'Qty', 'Unit Price', 'Line Total',
                'Order Subtotal', 'Discount', 'Order Total'])
    for i in items:
        o = i.order
        w.writerow([
            o.order_no,
            o.created_at.strftime('%Y-%m-%d %H:%M'),
            o.order_type,
            o.table_no or '—',
            i.product.category.name if i.product.category else '—',
            i.product.name,
            i.qty,
            i.unit_price,
            i.line_total,
            o.subtotal,
            o.discount_amount,
            o.grand_total,
        ])
    return response


@login_required(login_url='/login/')
def export_products_csv(request):
    """Download top products: qty sold and revenue per item."""
    date_from, date_to, start, end, _ = _date_range(request)
    rows = (
        OrderItem.objects
        .filter(order__status='PAID', order__created_at__gte=start, order__created_at__lte=end)
        .values('product__name', 'product__category__name')
        .annotate(qty_sold=Sum('qty'), revenue=Sum('line_total'))
        .order_by('-revenue')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="yasumi_products_{date_from}_{date_to}.csv"'
    )
    w = csv.writer(response)
    w.writerow(['Category', 'Item Name', 'Qty Sold', 'Revenue (Rs.)'])
    total_qty = total_rev = 0
    for r in rows:
        w.writerow([
            r['product__category__name'] or '—',
            r['product__name'],
            r['qty_sold'],
            r['revenue'],
        ])
        total_qty += r['qty_sold'] or 0
        total_rev += r['revenue'] or 0
    w.writerow([])
    w.writerow(['TOTAL', '', total_qty, total_rev])
    return response


@login_required(login_url='/login/')
def export_payments_csv(request):
    """Download payment transactions."""
    date_from, date_to, start, end, _ = _date_range(request)
    payments = (
        Payment.objects
        .filter(paid_at__gte=start, paid_at__lte=end)
        .select_related('order')
        .order_by('paid_at')
    )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="yasumi_payments_{date_from}_{date_to}.csv"'
    )
    w = csv.writer(response)
    w.writerow(['Order No', 'Method', 'Amount (Rs.)', 'Reference', 'Date', 'Time'])
    total = 0
    for p in payments:
        w.writerow([
            p.order.order_no,
            p.method,
            p.amount,
            p.txn_ref or '—',
            p.paid_at.strftime('%Y-%m-%d'),
            p.paid_at.strftime('%H:%M'),
        ])
        total += p.amount
    w.writerow([])
    w.writerow(['TOTAL', '', total, '', '', ''])
    return response
