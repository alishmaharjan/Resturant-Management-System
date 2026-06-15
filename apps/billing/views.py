import csv
from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
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


@login_required(login_url='/login/')
def export_credit_summary_csv(request):
    """Download all credit accounts with balance summary."""
    today = timezone.now().date()
    accounts = CreditAccount.objects.prefetch_related('records').order_by('name')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="yasumi_credit_summary_{today}.csv"'
    )
    w = csv.writer(response)
    w.writerow(['Customer', 'Phone', 'Since', 'Total Credit (Rs.)',
                'Total Repaid (Rs.)', 'Balance Due (Rs.)'])

    grand_credit = grand_repaid = Decimal('0')
    for acc in accounts:
        tc = acc.records.filter(record_type='CREDIT').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        tr = acc.records.filter(record_type='REPAYMENT').aggregate(t=Sum('amount'))['t'] or Decimal('0')
        bal = tc - tr
        grand_credit += tc
        grand_repaid += tr
        w.writerow([
            acc.name,
            acc.phone or '—',
            acc.created_at.strftime('%Y-%m-%d'),
            tc, tr, bal,
        ])

    w.writerow([])
    w.writerow(['TOTAL', '', '', grand_credit, grand_repaid, grand_credit - grand_repaid])
    return response


@login_required(login_url='/login/')
def export_credit_detail_csv(request, pk):
    """Download full transaction history for one credit account."""
    account = get_object_or_404(CreditAccount, pk=pk)
    records = account.records.select_related('order').order_by('created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="yasumi_credit_{account.name}_{timezone.now().date()}.csv"'
    )
    w = csv.writer(response)
    w.writerow([f'Credit Statement — {account.name}', '', '', '', ''])
    w.writerow(['Phone', account.phone or '—', '', '', ''])
    w.writerow([])
    w.writerow(['Date', 'Type', 'Order No.', 'Notes', 'Amount (Rs.)'])

    running = Decimal('0')
    for r in records:
        sign = 1 if r.record_type == 'CREDIT' else -1
        running += sign * r.amount
        w.writerow([
            r.created_at.strftime('%Y-%m-%d %H:%M'),
            r.record_type,
            r.order.order_no if r.order else '—',
            r.notes or '—',
            r.amount if r.record_type == 'CREDIT' else f'-{r.amount}',
        ])

    w.writerow([])
    w.writerow(['', '', '', 'Balance Due', running if running > 0 else 0])
    return response
