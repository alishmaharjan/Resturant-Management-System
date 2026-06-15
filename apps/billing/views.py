from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Value, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from .models import Payment, CreditAccount, CreditRecord, Refund


def _annotate_refunds(qs):
    """Annotate a Payment queryset with refunded_total per payment (safe subquery)."""
    refund_sub = (
        Refund.objects
        .filter(payment=OuterRef('pk'))
        .values('payment')
        .annotate(s=Sum('amount'))
        .values('s')[:1]
    )
    return qs.annotate(
        refunded_total=Coalesce(
            Subquery(refund_sub, output_field=DecimalField()),
            Value(Decimal('0'), output_field=DecimalField()),
        )
    )


@login_required(login_url='/login/')
def billing_list(request):
    qs = Payment.objects.select_related('order').all()

    method    = request.GET.get('method', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    if method:
        qs = qs.filter(method=method)
    if date_from:
        try:
            qs = qs.filter(paid_at__date__gte=date_from)
        except Exception:
            pass
    if date_to:
        try:
            qs = qs.filter(paid_at__date__lte=date_to)
        except Exception:
            pass

    total_amount  = qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_refunds = Refund.objects.filter(payment__in=qs).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    net_total     = total_amount - total_refunds

    qs = _annotate_refunds(qs)
    payments_raw = list(qs[:300])
    for p in payments_raw:
        p.refundable        = p.amount - (p.refunded_total or Decimal('0'))
        p.is_fully_refunded = p.refundable <= 0

    return render(request, 'billing/list.html', {
        'payments':      payments_raw,
        'total_amount':  total_amount,
        'total_refunds': total_refunds,
        'net_total':     net_total,
        'method':        method,
        'date_from':     date_from,
        'date_to':       date_to,
        'methods':       Payment.MethodChoices.choices,
    })


@login_required(login_url='/login/')
def refund_payment(request, pk):
    if request.method != 'POST':
        return redirect('billing_list')

    payment    = get_object_or_404(Payment, pk=pk)
    amount_str = request.POST.get('amount', '').strip()
    reason     = request.POST.get('reason', '').strip()

    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError('Amount must be positive')

        already_refunded = payment.refunds.aggregate(t=Sum('amount'))['t'] or Decimal('0')
        max_refundable   = payment.amount - already_refunded

        if amount > max_refundable:
            messages.error(
                request,
                f'Cannot refund Rs. {amount}. Maximum refundable amount is Rs. {max_refundable}.'
            )
            return redirect('billing_list')

        Refund.objects.create(payment=payment, amount=amount, reason=reason)

        try:
            from apps.reports.models import AuditLog
            AuditLog.objects.create(
                event_type='PAYMENT',
                action='Refund',
                message=f'Rs. {amount} refunded — {reason or "no reason given"} (Order {payment.order.order_no})',
                reference_id=str(payment.order.order_no),
            )
        except Exception:
            pass

        messages.success(request, f'Refund of Rs. {amount} recorded successfully.')
    except (InvalidOperation, ValueError) as e:
        messages.error(request, f'Invalid amount: {e}')

    return redirect('billing_list')


@login_required(login_url='/login/')
def credit_list(request):
    accounts = CreditAccount.objects.all()
    data = []
    for acc in accounts:
        total_credit = acc.records.filter(record_type='CREDIT').aggregate(t=Sum('amount'))['t'] or 0
        total_repaid = acc.records.filter(record_type='REPAYMENT').aggregate(t=Sum('amount'))['t'] or 0
        balance      = total_credit - total_repaid
        data.append({'account': acc, 'credit': total_credit, 'repaid': total_repaid, 'balance': balance})
    return render(request, 'billing/credits.html', {'data': data})


@login_required(login_url='/login/')
def credit_detail(request, pk):
    account      = get_object_or_404(CreditAccount, pk=pk)
    records      = account.records.select_related('order').all()
    total_credit = records.filter(record_type='CREDIT').aggregate(t=Sum('amount'))['t'] or 0
    total_repaid = records.filter(record_type='REPAYMENT').aggregate(t=Sum('amount'))['t'] or 0
    balance      = total_credit - total_repaid
    return render(request, 'billing/credit_detail.html', {
        'account':      account,
        'records':      records,
        'total_credit': total_credit,
        'total_repaid': total_repaid,
        'balance':      balance,
    })


@login_required(login_url='/login/')
def credit_repay(request, pk):
    if request.method == 'POST':
        account    = get_object_or_404(CreditAccount, pk=pk)
        amount_str = request.POST.get('amount', '').strip()
        notes      = request.POST.get('notes', '').strip()
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError
            CreditRecord.objects.create(
                account=account, record_type='REPAYMENT',
                amount=amount, notes=notes
            )
            messages.success(request, f'Repayment of Rs. {amount} recorded.')
        except (InvalidOperation, ValueError):
            messages.error(request, 'Enter a valid amount.')
    return redirect('credit_detail', pk=pk)
