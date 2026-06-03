from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import Payment, CreditAccount, CreditRecord


@login_required(login_url='/login/')
def billing_list(request):
    qs = Payment.objects.select_related('order').all()

    method     = request.GET.get('method', '')
    date_from  = request.GET.get('date_from', '')
    date_to    = request.GET.get('date_to', '')

    if method:    qs = qs.filter(method=method)
    if date_from:
        try: qs = qs.filter(paid_at__date__gte=date_from)
        except Exception: pass
    if date_to:
        try: qs = qs.filter(paid_at__date__lte=date_to)
        except Exception: pass

    payments    = qs[:300]
    total_amount = qs.aggregate(t=Sum('amount'))['t'] or 0

    return render(request, 'billing/list.html', {
        'payments':     payments,
        'total_amount': total_amount,
        'method':       method,
        'date_from':    date_from,
        'date_to':      date_to,
        'methods':      Payment.MethodChoices.choices,
    })


@login_required(login_url='/login/')
def credit_list(request):
    accounts = CreditAccount.objects.all()
    data = []
    for acc in accounts:
        total_credit  = acc.records.filter(record_type='CREDIT').aggregate(t=Sum('amount'))['t'] or 0
        total_repaid  = acc.records.filter(record_type='REPAYMENT').aggregate(t=Sum('amount'))['t'] or 0
        balance       = total_credit - total_repaid
        data.append({'account': acc, 'credit': total_credit, 'repaid': total_repaid, 'balance': balance})
    return render(request, 'billing/credits.html', {'data': data})


@login_required(login_url='/login/')
def credit_detail(request, pk):
    account = get_object_or_404(CreditAccount, pk=pk)
    records = account.records.select_related('order').all()
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
