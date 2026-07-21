import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.menu.models import Category, MenuItem
from apps.tables.models import Table
from apps.orders.models import Order, OrderItem
from apps.billing.models import Payment, CreditAccount, CreditRecord
from apps.reports.models import AuditLog
from functools import wraps


# ── Helpers ──────────────────────────────────────────────────────────────────

def _json(request):
    try:
        return json.loads(request.body)
    except:
        return {}

def _ok(data=None, msg='OK', status=200):
    return JsonResponse({'success': True, 'message': msg, 'data': data or {}}, status=status)

def _err(msg, status=400):
    return JsonResponse({'success': False, 'message': msg}, status=status)

def _audit(event_type, action, message, ref=''):
    AuditLog.objects.create(event_type=event_type, action=action, message=message[:255], reference_id=str(ref)[:80])

def _next_order_no():
    prefix = f"YSM-{timezone.now().strftime('%Y%m%d')}-"
    last = Order.objects.filter(order_no__startswith=prefix).order_by('-order_no').values_list('order_no', flat=True).first()
    seq = 1
    if last:
        try: seq = int(last.split('-')[-1]) + 1
        except: seq = 1
    return f'{prefix}{seq:04d}'

def _order_payload(order):
    items = [{'item_id': i.id, 'product_id': i.product_id, 'product_name': i.product.name,
               'qty': i.qty, 'unit_price': str(i.unit_price), 'line_total': str(i.line_total)}
             for i in order.items.select_related('product').all()]
    payments = [{'method': p.method, 'amount': str(p.amount), 'txn_ref': p.txn_ref}
                for p in order.payments.all()]
    credit_records = [{'customer_name': cr.account.name, 'amount': str(cr.amount), 'notes': cr.notes}
                      for cr in order.credit_records.select_related('account').filter(record_type='CREDIT')]
    return {'id': order.id, 'order_no': order.order_no, 'order_type': order.order_type,
            'table_no': order.table_no, 'status': order.status, 'subtotal': str(order.subtotal),
            'tax_amount': str(order.tax_amount), 'discount_amount': str(order.discount_amount),
            'grand_total': str(order.grand_total), 'payment_status': order.payment_status,
            'notes': order.notes, 'created_at': order.created_at.isoformat(),
            'items': items, 'payments': payments, 'credit_records': credit_records}

def api_auth(f):
    @wraps(f)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _err('Login required', 401)
        return f(request, *args, **kwargs)
    return wrapper

def recompute_totals(order):
    subtotal = sum(i.line_total for i in order.items.all())
    order.subtotal    = subtotal
    order.tax_amount  = Decimal('0')
    order.grand_total = subtotal - order.discount_amount
    order.save(update_fields=['subtotal', 'tax_amount', 'grand_total'])


# ── Page Views ────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('pos')
    error = None
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect('pos')
        error = 'Invalid username or password.'
    return render(request, 'login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='/login/')
def pos_view(request):
    return render(request, 'pos.html', {'user': request.user})

@login_required(login_url='/login/')
def dashboard_view(request):
    if not request.user.is_staff:
        return redirect('pos')

    today = timezone.now().date()
    tz = timezone.get_current_timezone()
    start = timezone.datetime.combine(today, timezone.datetime.min.time()).replace(tzinfo=tz)
    end   = timezone.datetime.combine(today, timezone.datetime.max.time()).replace(tzinfo=tz)

    active_statuses = ['OPEN', 'CONFIRMED', 'PREPARING', 'SERVED']
    total_tables  = Table.objects.filter(is_active=True).count()
    occupied      = (Order.objects.filter(status__in=active_statuses, table_no__isnull=False)
                     .exclude(table_no='').values('table_no').distinct().count())
    active_orders = Order.objects.filter(status__in=active_statuses).count()

    paid_today    = Order.objects.filter(status='PAID', created_at__gte=start, created_at__lte=end)
    revenue_agg   = paid_today.aggregate(total=Sum('grand_total'))
    today_revenue = revenue_agg['total'] or 0

    recent_orders = Order.objects.order_by('-created_at').select_related()[:20]

    return render(request, 'dashboard/index.html', {
        'user':           request.user,
        'total_tables':   total_tables,
        'occupied_tables': occupied,
        'active_orders':  active_orders,
        'today_revenue':  f'{today_revenue:,.2f}',
        'recent_orders':  recent_orders,
    })


# ── API: Tables ───────────────────────────────────────────────────────────────

@api_auth
@csrf_exempt
def api_tables(request):
    tables = Table.objects.filter(is_active=True)
    active_orders = Order.objects.filter(
        status__in=['OPEN','CONFIRMED','PREPARING','SERVED'],
        table_no__isnull=False
    ).exclude(table_no='').values('table_no', 'id', 'order_no', 'grand_total')
    order_map = {o['table_no']: o for o in active_orders}
    result = []
    for t in tables:
        active = order_map.get(t.name)
        result.append({'id': t.id, 'name': t.name, 'capacity': t.capacity,
                        'status': 'OCCUPIED' if active else 'FREE',
                        'order_id': active['id'] if active else None,
                        'order_no': active['order_no'] if active else None})
    return _ok(result)


# ── API: Menu ─────────────────────────────────────────────────────────────────

@api_auth
@csrf_exempt
def api_categories(request):
    cats = Category.objects.filter(is_active=True)
    return _ok([{'id': c.id, 'name': c.name} for c in cats])

@api_auth
@csrf_exempt
def api_products(request):
    qs = MenuItem.objects.filter(is_available=True).select_related('category')
    cat_id = request.GET.get('category_id')
    if cat_id:
        qs = qs.filter(category_id=cat_id)
    return _ok([{'id': p.id, 'name': p.name, 'price': str(p.price),
                  'tax_percent': str(p.tax_percent),
                  'category_id': p.category_id,
                  'category_name': p.category.name if p.category else ''} for p in qs])


# ── API: Orders ───────────────────────────────────────────────────────────────

@api_auth
@csrf_exempt
def api_orders(request):
    if request.method == 'GET':
        active_only = request.GET.get('active_only') == 'true'
        qs = Order.objects.prefetch_related('items__product', 'payments')
        if active_only:
            qs = qs.filter(status__in=['OPEN','CONFIRMED','PREPARING','SERVED'])
        else:
            qs = qs[:50]
        return _ok([_order_payload(o) for o in qs])

    body = _json(request)
    order_type = body.get('order_type', 'DINE_IN').upper()
    table_no   = body.get('table_no') or None
    order = Order.objects.create(
        order_no=_next_order_no(), order_type=order_type, table_no=table_no,
        notes=body.get('notes', '')
    )
    for item_data in body.get('items', []):
        try:
            product = MenuItem.objects.get(pk=item_data['product_id'], is_available=True)
            qty = max(1, int(item_data.get('qty', 1)))
            OrderItem.objects.create(order=order, product=product, qty=qty, unit_price=product.price)
        except MenuItem.DoesNotExist:
            continue
    recompute_totals(order)
    _audit('ORDER', 'create', f'Order {order.order_no} created', order.id)
    return _ok(_order_payload(order), status=201)

@api_auth
@csrf_exempt
def api_order_detail(request, order_id):
    try:
        order = Order.objects.prefetch_related('items__product', 'payments').get(pk=order_id)
    except Order.DoesNotExist:
        return _err('Order not found', 404)
    return _ok(_order_payload(order))

@api_auth
@csrf_exempt
def api_add_item(request, order_id):
    body = _json(request)
    try:
        order   = Order.objects.get(pk=order_id)
        product = MenuItem.objects.get(pk=body['product_id'], is_available=True)
    except (Order.DoesNotExist, MenuItem.DoesNotExist, KeyError):
        return _err('Not found', 404)
    if order.status in ['PAID', 'CANCELLED']:
        return _err('Cannot modify closed order')

    # delta can be negative (−1 = subtract, +1 = add)
    delta    = int(body.get('qty', 1))
    existing = order.items.filter(product=product).first()

    if existing:
        new_qty = existing.qty + delta
        if new_qty <= 0:
            existing.delete()           # remove item when qty hits 0
        else:
            existing.qty = new_qty
            existing.save()
    else:
        if delta > 0:                   # only create if adding, not subtracting
            OrderItem.objects.create(
                order=order, product=product, qty=delta, unit_price=product.price
            )

    recompute_totals(order)
    return _ok(_order_payload(order))

@api_auth
@csrf_exempt
def api_checkout(request, order_id):
    body = _json(request)
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return _err('Order not found', 404)
    if order.status == 'PAID':
        return _err('Already paid')
    if order.status == 'CANCELLED':
        return _err('Order cancelled')

    raw_payments = body.get('payments', [])
    if not raw_payments:
        return _err('No payments provided')

    discount = Decimal(str(body.get('discount', '0')))
    if discount > 0:
        order.discount_amount = discount
        order.grand_total = max(order.subtotal + order.tax_amount - discount, Decimal('0'))
        order.save(update_fields=['discount_amount', 'grand_total'])

    for p in raw_payments:
        method = str(p.get('method', '')).upper()
        try:
            amount = Decimal(str(p.get('amount', '')))
        except InvalidOperation:
            return _err(f'Invalid amount for {method}')

        if method == 'CREDIT':
            customer_name = str(p.get('customer_name', '')).strip()
            if not customer_name:
                return _err('Customer name required for credit')
            account, _ = CreditAccount.objects.get_or_create(name__iexact=customer_name,
                defaults={'name': customer_name, 'phone': str(p.get('phone', ''))})
            CreditRecord.objects.create(account=account, record_type='CREDIT',
                amount=amount, order=order, notes=str(p.get('notes', '')))
        else:
            Payment.objects.create(order=order, method=method, amount=amount,
                txn_ref=str(p.get('txn_ref', '')))

    order.status = 'PAID'
    order.payment_status = 'PAID'
    order.updated_at = timezone.now()
    order.save(update_fields=['status', 'payment_status', 'updated_at'])
    _audit('PAYMENT', 'checkout', f'Order {order.order_no} paid', order.id)
    return _ok(_order_payload(order))

@api_auth
@csrf_exempt
def api_cancel_order(request, order_id):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return _err('Not found', 404)
    if order.status in ['PAID', 'CANCELLED']:
        return _err(f'Cannot cancel order in status {order.status}')
    order.status = 'CANCELLED'
    order.updated_at = timezone.now()
    order.save(update_fields=['status', 'updated_at'])
    _audit('ORDER', 'cancel', f'Order {order.order_no} cancelled', order.id)
    return _ok(_order_payload(order))


# ── API: Dashboard ────────────────────────────────────────────────────────────

@api_auth
@csrf_exempt
def api_dashboard(request):
    today = timezone.now().date()
    start = timezone.datetime.combine(today, timezone.datetime.min.time()).replace(tzinfo=timezone.get_current_timezone())
    end   = timezone.datetime.combine(today, timezone.datetime.max.time()).replace(tzinfo=timezone.get_current_timezone())
    paid  = Order.objects.filter(status='PAID', created_at__gte=start, created_at__lte=end)
    agg   = paid.aggregate(gross=Sum('grand_total'), count=Count('id'))
    active = Order.objects.filter(status__in=['OPEN','CONFIRMED','PREPARING','SERVED']).count()
    top = (OrderItem.objects.filter(order__status='PAID', order__created_at__gte=start)
           .values('product__name').annotate(qty=Sum('qty'), rev=Sum('line_total')).order_by('-rev')[:8])
    payments = (Payment.objects.filter(paid_at__gte=start)
                .values('method').annotate(total=Sum('amount'), count=Count('id')))
    return _ok({
        'today_revenue' : str(agg['gross'] or 0),
        'today_orders'  : agg['count'] or 0,
        'active_orders' : active,
        'top_products'  : [{'name': t['product__name'], 'qty': t['qty'], 'revenue': str(t['rev'] or 0)} for t in top],
        'payment_breakdown': [{'method': p['method'], 'total': str(p['total'] or 0), 'count': p['count']} for p in payments],
    })

@api_auth
@csrf_exempt
def api_activity(request):
    logs = AuditLog.objects.all()[:30]
    return _ok([{'type': l.event_type, 'action': l.action, 'message': l.message,
                  'timestamp': l.created_at.strftime('%H:%M')} for l in logs])
