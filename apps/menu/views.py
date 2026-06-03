from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Category, MenuItem


def _staff(request):
    if not request.user.is_staff:
        messages.error(request, 'Staff access required.')
        return redirect('/')
    return None


# ── Category views ─────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def menu_list(request):
    categories  = Category.objects.prefetch_related('products').all()
    total_items = MenuItem.objects.count()
    avail_items = MenuItem.objects.filter(is_available=True).count()
    return render(request, 'menu/list.html', {
        'categories':  categories,
        'total_items': total_items,
        'avail_items': avail_items,
    })


@login_required(login_url='/login/')
def category_add(request):
    g = _staff(request)
    if g: return g
    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            error = 'Category name is required.'
        elif Category.objects.filter(name__iexact=name).exists():
            error = f'"{name}" already exists.'
        else:
            Category.objects.create(name=name)
            messages.success(request, f'Category "{name}" created.')
            return redirect('menu_list')
    return render(request, 'menu/category_form.html', {'action': 'Add', 'obj': None, 'error': error})


@login_required(login_url='/login/')
def category_edit(request, pk):
    g = _staff(request)
    if g: return g
    cat   = get_object_or_404(Category, pk=pk)
    error = None
    if request.method == 'POST':
        name      = request.POST.get('name', '').strip()
        is_active = 'is_active' in request.POST
        if not name:
            error = 'Name is required.'
        else:
            cat.name = name; cat.is_active = is_active; cat.save()
            messages.success(request, 'Category updated.')
            return redirect('menu_list')
    return render(request, 'menu/category_form.html', {'action': 'Edit', 'obj': cat, 'error': error})


@login_required(login_url='/login/')
def category_delete(request, pk):
    g = _staff(request)
    if g: return g
    if request.method == 'POST':
        cat = get_object_or_404(Category, pk=pk)
        name = cat.name; cat.delete()
        messages.success(request, f'"{name}" deleted.')
    return redirect('menu_list')


@login_required(login_url='/login/')
def category_toggle(request, pk):
    g = _staff(request)
    if g: return g
    if request.method == 'POST':
        cat = get_object_or_404(Category, pk=pk)
        cat.is_active = not cat.is_active; cat.save()
    return redirect('menu_list')


# ── Item views ─────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def item_add(request):
    g = _staff(request)
    if g: return g
    categories = Category.objects.all()
    error = None
    if request.method == 'POST':
        name      = request.POST.get('name', '').strip()
        cat_id    = request.POST.get('category')
        price_str = request.POST.get('price', '').strip()
        tax_str   = request.POST.get('tax_percent', '13').strip() or '13'
        is_avail  = 'is_available' in request.POST
        if not name:
            error = 'Name is required.'
        else:
            try:
                price = Decimal(price_str); tax = Decimal(tax_str)
                cat   = Category.objects.filter(pk=cat_id).first()
                MenuItem.objects.create(
                    name=name, category=cat, price=price,
                    tax_percent=tax, is_available=is_avail
                )
                messages.success(request, f'"{name}" added to menu.')
                return redirect('menu_list')
            except InvalidOperation:
                error = 'Enter a valid price.'
    return render(request, 'menu/item_form.html', {
        'action': 'Add', 'obj': None, 'categories': categories, 'error': error,
    })


@login_required(login_url='/login/')
def item_edit(request, pk):
    g = _staff(request)
    if g: return g
    item = get_object_or_404(MenuItem, pk=pk)
    categories = Category.objects.all()
    error = None
    if request.method == 'POST':
        name      = request.POST.get('name', '').strip()
        cat_id    = request.POST.get('category')
        price_str = request.POST.get('price', '').strip()
        tax_str   = request.POST.get('tax_percent', '13').strip() or '13'
        is_avail  = 'is_available' in request.POST
        if not name:
            error = 'Name is required.'
        else:
            try:
                item.name        = name
                item.category    = Category.objects.filter(pk=cat_id).first()
                item.price       = Decimal(price_str)
                item.tax_percent = Decimal(tax_str)
                item.is_available = is_avail
                item.save()
                messages.success(request, f'"{name}" updated.')
                return redirect('menu_list')
            except InvalidOperation:
                error = 'Enter a valid price.'
    return render(request, 'menu/item_form.html', {
        'action': 'Edit', 'obj': item, 'categories': categories, 'error': error,
    })


@login_required(login_url='/login/')
def item_delete(request, pk):
    g = _staff(request)
    if g: return g
    if request.method == 'POST':
        item = get_object_or_404(MenuItem, pk=pk)
        name = item.name
        try:
            item.delete()
            messages.success(request, f'"{name}" deleted.')
        except Exception:
            messages.error(request, f'Cannot delete "{name}" — referenced by existing orders.')
    return redirect('menu_list')


@login_required(login_url='/login/')
def item_toggle(request, pk):
    g = _staff(request)
    if g: return g
    if request.method == 'POST':
        item = get_object_or_404(MenuItem, pk=pk)
        item.is_available = not item.is_available; item.save()
    return redirect('menu_list')
