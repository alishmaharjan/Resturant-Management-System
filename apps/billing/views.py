import csv
from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Value, OuterRef, Subquery, Q, DecimalField
from django.db.models.functions import Coalesce
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
    method    = request.GET.get('method', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    # ── Payment records ───────────────────────────────────────────────────────
    pay_qs = Payment.objects.select_related('order').all()
    if method == 'CREDIT':
        pay_qs = pay_qs.none()
    elif method:
        pay_qs = pay_qs.filter(method=method)
    if date_from:
        try:
            pay_qs = pay_qs.filter(paid_at__date__gte=date_from)
        except Exception:
            pass
    if date_to:
        try:
            pay_qs = pay_qs.filter(paid_at__date__lte=date_to)
        except Exception:
            pass
    pay_qs = _annotate_refunds(pay_qs)
    payments_raw = list(pay_qs[:400])
    for p in payments_raw:
        p.refundable        = p.amount - (p.refunded_total or Decimal('0'))
        p.is_fully_refunded = p.refundable <= 0

    # ── CreditRecord (CREDIT only) ────────────────────────────────────────────
    cr_qs = CreditRecord.objects.filter(record_type='CREDIT').select_related('order', 'account').all()
    if method and method != 'CREDIT':
        cr_qs = cr_qs.none()
    if date_from:
        try:
            cr_qs = cr_qs.filter(created_at__date__gte=date_from)
        except Exception:
            pass
    if date_to:
        try:
            cr_qs = cr_qs.filter(created_at__date__lte=date_to)
        except Exception:
            pass
    cr_list = list(cr_qs[:400])

    # Bulk check which credit records already have a WRITEOFF
    written_off_pairs = set(
        CreditRecord.objects
        .filter(record_type='WRITEOFF')
        .exclude(order__isnull=True)
        .values_list('account_id', 'order_id')
    )
    for cr in cr_list:
        cr.is_written_off = (cr.account_id, cr.order_id) in written_off_pairs if cr.order_id else False
        cr.refundable      = Decimal('0') if cr.is_written_off else cr.amount

    # ── Build unified rows ────────────────────────────────────────────────────
    rows = []
    for p in payments_raw:
        rows.append({
            'kind':             'payment',
            'pk':               p.id,
            'order':            p.order,
            'method':           p.method,
            'amount':           p.amount,
            'txn_ref':          p.txn_ref or '',
            'date':             p.paid_at,
            'refunded_total':   p.refunded_total or Decimal('0'),
            'is_fully_refunded': p.is_fully_refunded,
            'refundable':       p.refundable,
            'customer':         None,
            'account_pk':       None,
        })
    for cr in cr_list:
        rows.append({
            'kind':             'credit',
            'pk':               cr.pk,
            'order':            cr.order,
            'method':           'CREDIT',
            'amount':           cr.amount,
            'txn_ref':          cr.notes or '',
            'date':             cr.created_at,
            'refunded_total':   cr.amount if cr.is_written_off else Decimal('0'),
            'is_fully_refunded': cr.is_written_off,
            'refundable':       cr.refundable,
            'customer':         cr.account.name,
            'account_pk':       cr.account.pk,
        })
    rows.sort(key=lambda r: r['date'], reverse=True)

    # ── Totals ────────────────────────────────────────────────────────────────
    total_pay_amount  = sum(r['amount'] for r in rows if r['kind'] == 'payment')
    total_cr_amount   = sum(r['amount'] for r in rows if r['kind'] == 'credit')
    total_amount      = total_pay_amount + total_cr_amount

    pay_ids           = [r['pk'] for r in rows if r['kind'] == 'payment']
    total_pay_refunds = (Refund.objects.filter(payment_id__in=pay_ids)
                         .aggregate(t=Sum('amount'))['t'] or Decimal('0')) if pay_ids else Decimal('0')
    total_writeoffs   = sum(r['amount'] for r in rows if r['kind'] == 'credit' and r['is_fully_refunded'])
    total_refunds     = total_pay_refunds + total_writeoffs

    cash_collected    = total_pay_amount - total_pay_refunds
    # Credit outstanding across ALL accounts (not just filtered view)
    all_cr = CreditRecord.objects.aggregate(
        c=Coalesce(Sum('amount', filter=Q(record_type='CREDIT')),    Value(Decimal('0'), output_field=DecimalField())),
        r=Coalesce(Sum('amount', filter=Q(record_type='REPAYMENT')), Value(Decimal('0'), output_field=DecimalField())),
        w=Coalesce(Sum('amount', filter=Q(record_type='WRITEOFF')),  Value(Decimal('0'), output_field=DecimalField())),
    )
    credit_outstanding = all_cr['c'] - all_cr['r'] - all_cr['w']

    return render(request, 'billing/list.html', {
        'rows':               rows,
        'total_amount':       total_amount,
        'total_refunds':      total_refunds,
        'cash_collected':     cash_collected,
        'credit_outstanding': credit_outstanding,
        'method':             method,
        'date_from':          date_from,
        'date_to':            date_to,
        'methods':            Payment.MethodChoices.choices,
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
        total_credit   = acc.records.filter(record_type='CREDIT').aggregate(t=Sum('amount'))['t'] or 0
        total_repaid   = acc.records.filter(record_type='REPAYMENT').aggregate(t=Sum('amount'))['t'] or 0
        total_writeoff = acc.records.filter(record_type='WRITEOFF').aggregate(t=Sum('amount'))['t'] or 0
        balance        = total_credit - total_repaid - total_writeoff
        data.append({'account': acc, 'credit': total_credit, 'repaid': total_repaid, 'balance': balance})
    return render(request, 'billing/credits.html', {'data': data})


@login_required(login_url='/login/')
def credit_detail(request, pk):
    account        = get_object_or_404(CreditAccount, pk=pk)
    records        = account.records.select_related('order').all()
    total_credit   = records.filter(record_type='CREDIT').aggregate(t=Sum('amount'))['t'] or 0
    total_repaid   = records.filter(record_type='REPAYMENT').aggregate(t=Sum('amount'))['t'] or 0
    total_writeoff = records.filter(record_type='WRITEOFF').aggregate(t=Sum('amount'))['t'] or 0
    balance        = total_credit - total_repaid - total_writeoff
    return render(request, 'billing/credit_detail.html', {
        'account':       account,
        'records':       records,
        'total_credit':  total_credit,
        'total_repaid':  total_repaid,
        'total_writeoff': total_writeoff,
        'balance':       balance,
    })


@login_required(login_url='/login/')
def refund_credit_record(request, pk):
    """Write off a specific credit record — reduces customer balance. Remarks mandatory."""
    if request.method != 'POST':
        return redirect('credit_list')

    record  = get_object_or_404(CreditRecord, pk=pk, record_type='CREDIT')
    remarks = request.POST.get('remarks', '').strip()

    if not remarks:
        messages.error(request, 'Remarks are required to refund a credit bill.')
        return redirect('credit_detail', pk=record.account.pk)

    already_written_off = CreditRecord.objects.filter(
        account=record.account,
        record_type='WRITEOFF',
        order=record.order,
    ).exists()
    if already_written_off:
        messages.error(request, 'This credit bill has already been refunded/written off.')
        return redirect('credit_detail', pk=record.account.pk)

    CreditRecord.objects.create(
        account     = record.account,
        record_type = 'WRITEOFF',
        amount      = record.amount,
        order       = record.order,
        notes       = f'REFUND: {remarks}',
    )

    try:
        from apps.reports.models import AuditLog
        AuditLog.objects.create(
            event_type   = 'PAYMENT',
            action       = 'Credit Refund',
            message      = (f'Credit Rs. {record.amount} refunded for {record.account.name}'
                            f' — {remarks}'
                            + (f' (Order {record.order.order_no})' if record.order else '')),
            reference_id = str(record.order.order_no if record.order else ''),
        )
    except Exception:
        pass

    messages.success(request, f'Credit of Rs. {record.amount} written off for {record.account.name}.')
    next_url = request.POST.get('next', '')
    if next_url == 'billing_list':
        return redirect('billing_list')
    return redirect('credit_detail', pk=record.account.pk)


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
            messages.success(request, f'Repayment of Rs. {amount} recorded for {account.name}.')
        except (InvalidOperation, ValueError):
            messages.error(request, 'Enter a valid amount.')
    next_url = request.POST.get('next', '')
    if next_url == 'credit_list':
        return redirect('credit_list')
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
