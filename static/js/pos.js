
// ── State ──────────────────────────────────────────────────────────────────
let state = {
  tables: [], categories: [], products: [],
  selectedTable: null, orderType: null,
  currentOrder: null, activePayMethod: null,
};

// ── Helpers ────────────────────────────────────────────────────────────────
async function api(path, options={}) {
  const res = await fetch(path, {
    headers: {'Content-Type':'application/json', 'X-CSRFToken': getCsrf()},
    ...options
  });
  const data = await res.json();
  if (!data.success) throw new Error(data.message || 'Request failed');
  return data.data;
}

function getCsrf() {
  return document.cookie.split(';').map(c=>c.trim())
    .find(c=>c.startsWith('csrftoken='))?.split('=')[1] || '';
}

function fmt(v) { return 'Rs. ' + parseFloat(v||0).toFixed(2); }

function showErr(msg) {
  const d = document.createElement('div');
  d.style.cssText = 'position:fixed;top:60px;right:16px;background:#2b0d0d;border:1px solid #c0392b;color:#ff8080;padding:10px 16px;border-radius:8px;z-index:9999;font-size:.85rem;';
  d.textContent = msg;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 3000);
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  init();
  setInterval(loadTables, 30000);
});

async function init() {
  await Promise.all([loadTables(), loadCategories(), loadProducts(null, '')]);
}

// ── Tables ─────────────────────────────────────────────────────────────────
async function loadTables() {
  try {
    state.tables = await api('/api/tables/');
    renderTables();
  } catch(e) { console.error('Tables error:', e); }
}

function renderTables() {
  const grid = document.getElementById('tableGrid');
  if (!state.tables.length) {
    grid.innerHTML = '<div style="color:#555;font-size:.7rem;padding:8px;grid-column:1/-1;">No tables.<br>Add from Admin.</div>';
    return;
  }
  grid.innerHTML = state.tables.map(t => `
    <button class="table-btn ${t.status==='OCCUPIED'?'occupied':'free'} ${state.selectedTable===t.name?'selected':''}"
      onclick="selectTable('${t.name}', ${t.order_id||'null'})">
      <div class="t-name">${t.name}</div>
      <div class="t-info">${t.status==='OCCUPIED' ? (t.order_no||'Occupied') : t.capacity+' seats'}</div>
    </button>
  `).join('');
}

function selectTable(name, existingOrderId) {
  state.selectedTable = name;
  state.orderType = 'DINE_IN';
  document.getElementById('takeawayBtn').classList.remove('selected');
  renderTables();
  document.getElementById('cartTitle').textContent = 'Table ' + name;
  document.getElementById('cartSub').textContent   = 'Dine In';
  if (existingOrderId) {
    loadExistingOrder(existingOrderId);
  } else {
    state.currentOrder = null;
    renderCart();
  }
  renderProducts();
}

function selectTakeaway() {
  state.selectedTable = null;
  state.orderType     = 'TAKEAWAY';
  renderTables();
  document.getElementById('takeawayBtn').classList.add('selected');
  document.getElementById('cartTitle').textContent = 'Takeaway';
  document.getElementById('cartSub').textContent   = 'Takeaway Order';
  state.currentOrder = null;
  renderCart();
  renderProducts();
}

async function loadExistingOrder(orderId) {
  try {
    state.currentOrder = await api('/api/orders/' + orderId + '/');
    renderCart();
  } catch(e) { console.error(e); }
}

// ── Categories & Products ──────────────────────────────────────────────────
async function loadCategories() {
  try {
    state.categories = await api('/api/categories/');
    const bar = document.getElementById('categoryBar');
    bar.innerHTML = `<button class="cat-btn active" onclick="loadProducts(this,'')" data-cat="">All</button>` +
      state.categories.map(c =>
        `<button class="cat-btn" onclick="loadProducts(this,'${c.id}')" data-cat="${c.id}">${c.name}</button>`
      ).join('');
  } catch(e) { console.error(e); }
}

async function loadProducts(btn, catId) {
  document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  try {
    const url = catId ? `/api/products/?category_id=${catId}` : '/api/products/';
    state.products = await api(url);
    renderProducts();
  } catch(e) { console.error(e); }
}

function renderProducts() {
  const grid = document.getElementById('productGrid');
  if (!state.orderType && !state.selectedTable) {
    grid.innerHTML = '<div style="color:#444;font-size:.85rem;padding:20px;grid-column:1/-1;">Select a table or takeaway to start.</div>';
    return;
  }
  if (!state.products.length) {
    grid.innerHTML = '<div style="color:#444;font-size:.85rem;padding:20px;grid-column:1/-1;">No items available.</div>';
    return;
  }
  grid.innerHTML = state.products.map(p => `
    <div class="prod-card" onclick="addToOrder(${p.id})">
      <div class="prod-name">${p.name}</div>
      <div class="prod-price">${fmt(p.price)}</div>
    </div>
  `).join('');
}

// ── Order ──────────────────────────────────────────────────────────────────
async function addToOrder(productId) {
  if (!state.orderType && !state.selectedTable) { showErr('Select a table first!'); return; }
  try {
    if (!state.currentOrder) {
      state.currentOrder = await api('/api/orders/', {
        method: 'POST',
        body: JSON.stringify({
          order_type: state.orderType || 'DINE_IN',
          table_no: state.selectedTable,
          items: [{product_id: productId, qty: 1}]
        })
      });
    } else {
      state.currentOrder = await api(`/api/orders/${state.currentOrder.id}/add-item/`, {
        method: 'POST',
        body: JSON.stringify({product_id: productId, qty: 1})
      });
    }
    renderCart();
    loadTables();
  } catch(e) { showErr(e.message); }
}

async function changeQty(itemId, productId, delta) {
  if (!state.currentOrder) return;
  try {
    state.currentOrder = await api(`/api/orders/${state.currentOrder.id}/add-item/`, {
      method: 'POST',
      body: JSON.stringify({product_id: productId, qty: delta})
    });
    renderCart();
  } catch(e) { showErr(e.message); }
}

async function cancelOrder() {
  if (!state.currentOrder) return;
  if (!confirm('Cancel this order?')) return;
  try {
    await api(`/api/orders/${state.currentOrder.id}/cancel/`, {method:'POST', body:'{}'});
    state.currentOrder = null;
    renderCart();
    loadTables();
  } catch(e) { showErr(e.message); }
}

function renderCart() {
  const container = document.getElementById('cartItems');
  const order     = state.currentOrder;
  const hasPaid   = order && order.status === 'PAID';
  const hasItems  = order && order.items && order.items.length > 0;

  ['btnCash','btnFonepay','btnSplit','btnCredit'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !hasItems || hasPaid;
  });
  document.getElementById('btnCancel').disabled = !order || hasPaid;

  if (!order || !order.items || !order.items.length) {
    container.innerHTML = '<div class="cart-empty"><i class="bi bi-cart3" style="font-size:2rem;display:block;margin-bottom:8px;color:#333;"></i>Cart is empty</div>';
    document.getElementById('tSubtotal').textContent = 'Rs. 0.00';
    document.getElementById('tTax').textContent      = 'Rs. 0.00';
    document.getElementById('tTotal').textContent    = 'Rs. 0.00';
    return;
  }

  container.innerHTML = order.items.map(item => `
    <div class="cart-item">
      <div class="cart-item-name">${item.product_name}</div>
      <div class="qty-ctrl">
        <button class="qty-btn" onclick="changeQty(${item.item_id},${item.product_id},-1)">−</button>
        <span class="qty-val">${item.qty}</span>
        <button class="qty-btn" onclick="changeQty(${item.item_id},${item.product_id},1)">+</button>
      </div>
      <div class="cart-item-price">${fmt(item.line_total)}</div>
    </div>
  `).join('');

  document.getElementById('tSubtotal').textContent = fmt(order.subtotal);
  document.getElementById('tTax').textContent      = fmt(order.tax_amount);
  document.getElementById('tTotal').textContent    = fmt(order.grand_total);

  if (hasPaid) document.getElementById('cartSub').textContent = '✅ PAID — Select new table';
}

// ── Single Payment Modal ───────────────────────────────────────────────────
function openPay(method) {
  if (!state.currentOrder) return;
  state.activePayMethod = method;
  const discount    = parseFloat(document.getElementById('discountInput').value || 0);
  const finalTotal  = Math.max(parseFloat(state.currentOrder.grand_total) - discount, 0);

  document.getElementById('payAmount').textContent = fmt(finalTotal);
  document.getElementById('payModalTitle').textContent =
    method === 'CASH'    ? '💴 Cash Payment'    :
    method === 'FONEPAY' ? '📱 FonePay QR'      : '👤 Credit Payment';

  document.getElementById('cashFields').style.display   = method === 'CASH'    ? '' : 'none';
  document.getElementById('qrFields').style.display     = method === 'FONEPAY' ? '' : 'none';
  document.getElementById('creditFields').style.display = method === 'CREDIT'  ? '' : 'none';

  if (method === 'FONEPAY') document.getElementById('qrLabel').textContent = 'FonePay QR';

  document.getElementById('cashTendered').value = '';
  document.getElementById('changeBox').classList.add('d-none');
  document.getElementById('txnRef').value      = '';
  document.getElementById('creditName').value  = '';
  document.getElementById('creditPhone').value = '';
  document.getElementById('creditNotes').value = '';
  document.getElementById('modalDiscount').value = discount || '';

  new bootstrap.Modal(document.getElementById('payModal')).show();
}

function calcChange() {
  const total      = parseFloat(state.currentOrder?.grand_total || 0);
  const discount   = parseFloat(document.getElementById('modalDiscount').value || 0);
  const finalTotal = Math.max(total - discount, 0);
  const tendered   = parseFloat(document.getElementById('cashTendered').value || 0);
  const box        = document.getElementById('changeBox');
  if (tendered > 0) {
    const change = tendered - finalTotal;
    box.textContent = change >= 0 ? `Change: ${fmt(change)}` : `⚠ Short by ${fmt(-change)}`;
    box.classList.remove('d-none');
    box.style.background = change >= 0 ? '#0d2b0d' : '#2b0d0d';
    box.style.color      = change >= 0 ? '#6fcf79' : '#ff8080';
    box.style.border     = change >= 0 ? '1px solid #2d7a35' : '1px solid #c0392b';
  }
}

async function confirmPayment() {
  if (!state.currentOrder) return;
  const method   = state.activePayMethod;
  const discount = parseFloat(document.getElementById('modalDiscount').value || 0);
  const total    = Math.max(parseFloat(state.currentOrder.grand_total) - discount, 0);
  const payment  = {method, amount: total};

  if (method === 'CASH') {
    const tendered = parseFloat(document.getElementById('cashTendered').value || 0);
    if (tendered < total) { showErr('Amount tendered is less than total!'); return; }
  } else if (method === 'FONEPAY') {
    payment.txn_ref = document.getElementById('txnRef').value;
  } else if (method === 'CREDIT') {
    const name = document.getElementById('creditName').value.trim();
    if (!name) { showErr('Customer name is required!'); return; }
    payment.customer_name = name;
    payment.phone         = document.getElementById('creditPhone').value;
    payment.notes         = document.getElementById('creditNotes').value;
  }

  try {
    const order = await api(`/api/orders/${state.currentOrder.id}/checkout/`, {
      method: 'POST',
      body: JSON.stringify({payments: [payment], discount})
    });
    state.currentOrder = order;
    bootstrap.Modal.getInstance(document.getElementById('payModal'))?.hide();
    renderCart();
    loadTables();
    showReceipt(order);
  } catch(e) { showErr(e.message); }
}

// ── Split Payment Modal ────────────────────────────────────────────────────
function openSplit() {
  if (!state.currentOrder) return;
  const total = parseFloat(state.currentOrder.grand_total);
  document.getElementById('splitTotal').textContent    = fmt(total);
  document.getElementById('splitCash').value           = '';
  document.getElementById('splitFonepay').value        = '';
  document.getElementById('splitCredit').value         = '';
  document.getElementById('splitTxnRef').value         = '';
  document.getElementById('splitCreditName').value     = '';
  document.getElementById('splitCreditPhone').value    = '';
  document.getElementById('splitRemaining').textContent = fmt(total);
  document.getElementById('splitCreditDetails').style.display = 'none';
  new bootstrap.Modal(document.getElementById('splitModal')).show();
}

function calcSplitRemainder() {
  const total   = parseFloat(state.currentOrder?.grand_total || 0);
  const cash    = parseFloat(document.getElementById('splitCash').value    || 0);
  const fonepay = parseFloat(document.getElementById('splitFonepay').value || 0);
  const credit  = parseFloat(document.getElementById('splitCredit').value  || 0);
  const left    = total - cash - fonepay - credit;
  document.getElementById('splitRemaining').textContent = fmt(Math.max(left, 0));
  document.getElementById('splitCreditDetails').style.display = credit > 0 ? '' : 'none';
}

async function confirmSplit() {
  if (!state.currentOrder) return;
  const total    = parseFloat(state.currentOrder.grand_total);
  const cash     = parseFloat(document.getElementById('splitCash').value    || 0);
  const fonepay  = parseFloat(document.getElementById('splitFonepay').value || 0);
  const credit   = parseFloat(document.getElementById('splitCredit').value  || 0);

  if (cash + fonepay + credit < total - 0.01) { showErr('Total paid is less than order total!'); return; }

  const payments = [];
  if (cash > 0)    payments.push({method:'CASH',    amount: cash});
  if (fonepay > 0) payments.push({method:'FONEPAY', amount: fonepay, txn_ref: document.getElementById('splitTxnRef').value});
  if (credit > 0) {
    const name = document.getElementById('splitCreditName').value.trim();
    if (!name) { showErr('Customer name required for credit!'); return; }
    payments.push({method:'CREDIT', amount: credit, customer_name: name,
                   phone: document.getElementById('splitCreditPhone').value});
  }

  try {
    const order = await api(`/api/orders/${state.currentOrder.id}/checkout/`, {
      method: 'POST',
      body: JSON.stringify({payments, discount: 0})
    });
    state.currentOrder = order;
    bootstrap.Modal.getInstance(document.getElementById('splitModal'))?.hide();
    renderCart();
    loadTables();
    showReceipt(order);
  } catch(e) { showErr(e.message); }
}

// ── Receipt ────────────────────────────────────────────────────────────────
function showReceipt(order) {
  const lines = order.items.map(i =>
    `${i.product_name.substring(0,16).padEnd(16)} x${i.qty}  ${fmt(i.line_total)}`
  ).join('\n');
  const payments = order.payments.map(p => `${p.method.padEnd(8)}: ${fmt(p.amount)}`).join('\n');
  document.getElementById('receiptBody').innerHTML = `
<pre style="color:#eee;margin:0;font-size:.78rem;">
━━━━━━━━━━━━━━━━━━━━━━━━━━
      休み  YASUMI
   Japanese Restaurant
━━━━━━━━━━━━━━━━━━━━━━━━━━
Order : ${order.order_no}
Type  : ${order.order_type}
Table : ${order.table_no || '—'}
━━━━━━━━━━━━━━━━━━━━━━━━━━
${lines}
━━━━━━━━━━━━━━━━━━━━━━━━━━
Subtotal  : ${fmt(order.subtotal)}
Tax (13%) : ${fmt(order.tax_amount)}
Discount  : ${fmt(order.discount_amount)}
TOTAL     : ${fmt(order.grand_total)}
━━━━━━━━━━━━━━━━━━━━━━━━━━
${payments}
━━━━━━━━━━━━━━━━━━━━━━━━━━
     Thank you! またね!
━━━━━━━━━━━━━━━━━━━━━━━━━━
</pre>`;
  new bootstrap.Modal(document.getElementById('receiptModal')).show();
}
