from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Order, OrderItem


STATUS_FLOW = {
    'OPEN':      'CONFIRMED',
    'CONFIRMED': 'PREPARING',
    'PREPARING': 'SERVED',
    'SERVED':    'PAID',
}

STATUS_LABELS = {
    'OPEN':      ('Confirm Order',    'bi-check-circle',    '#c8972b'),
    'CONFIRMED': ('Mark Preparing',   'bi-fire',            '#d4801e'),
    'PREPARING': ('Mark Served',      'bi-check2-all',      '#7ab0ff'),
    'SERVED':    ('Mark Paid (POS)',  'bi-cash-coin',       '#5daa80'),
}


@login_required(login_url='/login/')
def order_list(request):
    qs = Order.objects.prefetch_related('items').all()

    status    = request.GET.get('status', '')
    order_type= request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    search    = request.GET.get('q', '').strip()

    if status:     qs = qs.filter(status=status)
    if order_type: qs = qs.filter(order_type=order_type)
    if search:     qs = qs.filter(order_no__icontains=search)
    if date_from:
        try:
            qs = qs.filter(created_at__date__gte=date_from)
        except Exception: pass
    if date_to:
        try:
            qs = qs.filter(created_at__date__lte=date_to)
        except Exception: pass

    orders = qs[:200]
    return render(request, 'orders/list.html', {
        'orders': orders,
        'status': status, 'order_type': order_type,
        'date_from': date_from, 'date_to': date_to, 'search': search,
        'status_choices': Order.StatusChoices.choices,
        'type_choices':   Order.OrderTypeChoices.choices,
    })


@login_required(login_url='/login/')
def order_detail(request, pk):
    order    = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'payments', 'credit_records__account'),
        pk=pk
    )
    next_status     = STATUS_FLOW.get(order.status)
    next_label      = STATUS_LABELS.get(order.status)
    return render(request, 'orders/detail.html', {
        'order':       order,
        'next_status': next_status,
        'next_label':  next_label,
    })


@login_required(login_url='/login/')
def order_update_status(request, pk):
    if request.method == 'POST':
        order      = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get('status', '')
        allowed    = list(STATUS_FLOW.values()) + ['CANCELLED']
        if new_status in allowed and order.status not in ['PAID', 'CANCELLED']:
            order.status     = new_status
            order.updated_at = timezone.now()
            order.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'Order {order.order_no} → {new_status}')
        else:
            messages.error(request, 'Invalid status transition.')
    return redirect('order_detail', pk=pk)
