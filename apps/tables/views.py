from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Table
from apps.orders.models import Order


def _staff(request):
    if not request.user.is_staff:
        messages.error(request, 'Staff access required.')
        return redirect('/')
    return None


@login_required(login_url='/login/')
def table_list(request):
    tables = Table.objects.all()
    active_orders = {
        o['table_no']: o
        for o in Order.objects.filter(
            status__in=['OPEN', 'CONFIRMED', 'PREPARING', 'SERVED'],
            table_no__isnull=False
        ).exclude(table_no='').values('table_no', 'id', 'order_no', 'status', 'grand_total')
    }
    table_data = []
    for t in tables:
        order = active_orders.get(t.name)
        table_data.append({'table': t, 'order': order})
    return render(request, 'tables/list.html', {'table_data': table_data})


@login_required(login_url='/login/')
def table_add(request):
    g = _staff(request)
    if g: return g
    error = None
    if request.method == 'POST':
        name     = request.POST.get('name', '').strip().upper()
        capacity = request.POST.get('capacity', '4').strip()
        if not name:
            error = 'Table name is required.'
        elif Table.objects.filter(name__iexact=name).exists():
            error = f'Table "{name}" already exists.'
        else:
            try:
                Table.objects.create(name=name, capacity=int(capacity), is_active=True)
                messages.success(request, f'Table "{name}" added.')
                return redirect('table_list')
            except Exception:
                error = 'Invalid capacity value.'
    return render(request, 'tables/form.html', {'action': 'Add', 'obj': None, 'error': error})


@login_required(login_url='/login/')
def table_edit(request, pk):
    g = _staff(request)
    if g: return g
    table = get_object_or_404(Table, pk=pk)
    error = None
    if request.method == 'POST':
        name      = request.POST.get('name', '').strip().upper()
        capacity  = request.POST.get('capacity', '4').strip()
        is_active = 'is_active' in request.POST
        if not name:
            error = 'Table name is required.'
        else:
            try:
                table.name = name; table.capacity = int(capacity)
                table.is_active = is_active; table.save()
                messages.success(request, f'Table "{name}" updated.')
                return redirect('table_list')
            except Exception:
                error = 'Invalid values.'
    return render(request, 'tables/form.html', {'action': 'Edit', 'obj': table, 'error': error})


@login_required(login_url='/login/')
def table_delete(request, pk):
    g = _staff(request)
    if g: return g
    if request.method == 'POST':
        table = get_object_or_404(Table, pk=pk)
        name  = table.name
        table.delete()
        messages.success(request, f'Table "{name}" deleted.')
    return redirect('table_list')


@login_required(login_url='/login/')
def table_toggle(request, pk):
    g = _staff(request)
    if g: return g
    if request.method == 'POST':
        table = get_object_or_404(Table, pk=pk)
        table.is_active = not table.is_active; table.save()
    return redirect('table_list')
