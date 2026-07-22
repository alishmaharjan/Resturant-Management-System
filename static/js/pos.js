
// ── State ──────────────────────────────────────────────────────────────────
let state = {
  tables: [], categories: [], products: [],
  selectedTable: null, orderType: null,
  currentOrder: null, activePayMethod: null,
  lastReceiptOrder: null,
};

// ── Helpers ────────────────────────────────────────────────────────────────
async function api(path, options={}) {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers: {'Content-Type':'application/json', 'X-CSRFToken': getCsrf()},
    ...options
  });
  if (res.status === 401) {
    window.location.href = '/login/';
    return;
  }
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

function _resetDiscount() {
  document.getElementById('discountInput').value = '';
  document.getElementById('tTotal').textContent  = 'Rs. 0.00';
}

function selectTable(name, existingOrderId) {
  state.selectedTable = name;
  state.orderType = 'DINE_IN';
  document.getElementById('takeawayBtn').classList.remove('selected');
  renderTables();
  document.getElementById('cartTitle').textContent = 'Table ' + name;
  document.getElementById('cartSub').textContent   = 'Dine In';
  _resetDiscount();
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
  _resetDiscount();
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
    grid.innerHTML = `
      <div style="grid-column:1/-1;display:flex;align-items:center;justify-content:center;
                  height:calc(100vh - 120px);pointer-events:none;user-select:none;">
        <div style="color:#555;font-size:.78rem;letter-spacing:2px;text-transform:uppercase;
                    background:rgba(0,0,0,.5);padding:8px 18px;border-radius:20px;">
          Select a table or Takeaway to begin
        </div>
      </div>`;
    return;
  }
  const q = (document.getElementById('menuSearch')?.value || '').trim().toLowerCase();
  const products = q ? state.products.filter(p => p.name.toLowerCase().includes(q)) : state.products;
  if (!products.length) {
    grid.innerHTML = `<div style="color:#555;font-size:.85rem;padding:20px;grid-column:1/-1;text-align:center;">${q ? 'No items match your search.' : 'No items available.'}</div>`;
    return;
  }
  grid.innerHTML = products.map(p => `
    <div class="prod-card" onclick="addToOrder(${p.id})">
      <div class="prod-name">${p.name}</div>
      <div class="prod-price">${fmt(p.price)}</div>
    </div>
  `).join('');
}

function filterMenu(q) { renderProducts(); }

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

  ['btnCash','btnCard','btnFonepay','btnSplit','btnCredit'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = !hasItems || hasPaid;
  });
  document.getElementById('btnCancel').disabled = !order || hasPaid;

  if (!order || !order.items || !order.items.length) {
    container.innerHTML = '<div class="cart-empty"><i class="bi bi-cart3" style="font-size:2rem;display:block;margin-bottom:8px;color:#333;"></i>Cart is empty</div>';
    document.getElementById('tSubtotal').textContent = 'Rs. 0.00';
    document.getElementById('tTotal').textContent    = 'Rs. 0.00';
    document.getElementById('discountInput').value   = '';
    document.getElementById('discountInput').max     = '';
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

  // Set max discount = subtotal so browser validation catches it
  document.getElementById('discountInput').max = order.subtotal;

  document.getElementById('tSubtotal').textContent = fmt(order.subtotal);
  // Respect any already-typed discount when re-rendering
  const existingDiscount = parseFloat(document.getElementById('discountInput').value || 0);
  const displayTotal = Math.max(parseFloat(order.grand_total) - existingDiscount, 0);
  document.getElementById('tTotal').textContent = fmt(displayTotal);

  if (hasPaid) document.getElementById('cartSub').textContent = '✅ PAID — Select new table';
}

// ── Discount ───────────────────────────────────────────────────────────────
function applyDiscount() {
  if (!state.currentOrder) return;
  const subtotal = parseFloat(state.currentOrder.subtotal || 0);
  let discount   = parseFloat(document.getElementById('discountInput').value || 0);
  if (discount > subtotal) {
    discount = subtotal;
    document.getElementById('discountInput').value = subtotal;
  }
  const total = Math.max(subtotal - discount, 0);
  document.getElementById('tTotal').textContent = fmt(total);
}

// ── Single Payment Modal ───────────────────────────────────────────────────
function _getCartDiscount() {
  const subtotal = parseFloat(state.currentOrder?.subtotal || 0);
  const d = parseFloat(document.getElementById('discountInput').value || 0);
  return Math.min(Math.max(d, 0), subtotal); // clamp 0..subtotal
}

function openPay(method) {
  if (!state.currentOrder) return;
  state.activePayMethod = method;
  const discount   = _getCartDiscount();
  const finalTotal = Math.max(parseFloat(state.currentOrder.grand_total) - discount, 0);

  document.getElementById('payAmount').textContent = fmt(finalTotal);
  document.getElementById('payModalTitle').textContent =
    method === 'CASH'    ? '💴 Cash Payment'    :
    method === 'CARD'    ? '💳 Card Payment'    :
    method === 'FONEPAY' ? '📱 FonePay QR'      : '👤 Credit Payment';

  document.getElementById('cashFields').style.display   = method === 'CASH'    ? '' : 'none';
  document.getElementById('cardFields').style.display   = method === 'CARD'    ? '' : 'none';
  document.getElementById('qrFields').style.display     = method === 'FONEPAY' ? '' : 'none';
  document.getElementById('creditFields').style.display = method === 'CREDIT'  ? '' : 'none';

  document.getElementById('cashTendered').value = '';
  document.getElementById('changeBox').classList.add('d-none');
  document.getElementById('cardRef').value      = '';
  document.getElementById('txnRef').value       = '';
  document.getElementById('creditName').value   = '';
  document.getElementById('creditPhone').value  = '';
  document.getElementById('creditNotes').value  = '';

  // Show discount as read-only info (no editable field)
  const discountInfo = document.getElementById('discountInfo');
  if (discount > 0) {
    discountInfo.style.display = '';
    document.getElementById('discountInfoAmt').textContent = '− ' + fmt(discount);
  } else {
    discountInfo.style.display = 'none';
  }

  new bootstrap.Modal(document.getElementById('payModal')).show();
}

function calcChange() {
  const discount   = _getCartDiscount();
  const finalTotal = Math.max(parseFloat(state.currentOrder?.grand_total || 0) - discount, 0);
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
  const discount = _getCartDiscount();
  const total    = Math.max(parseFloat(state.currentOrder.grand_total) - discount, 0);
  const payment  = {method, amount: total};

  if (method === 'CASH') {
    const tendered = parseFloat(document.getElementById('cashTendered').value || 0);
    if (tendered < total) { showErr('Amount tendered is less than total!'); return; }
  } else if (method === 'CARD') {
    payment.txn_ref = document.getElementById('cardRef').value.trim();
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
  const discount = _getCartDiscount();
  const total = Math.max(parseFloat(state.currentOrder.grand_total) - discount, 0);
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
  const discount = _getCartDiscount();
  const total   = Math.max(parseFloat(state.currentOrder?.grand_total || 0) - discount, 0);
  const cash    = parseFloat(document.getElementById('splitCash').value    || 0);
  const fonepay = parseFloat(document.getElementById('splitFonepay').value || 0);
  const credit  = parseFloat(document.getElementById('splitCredit').value  || 0);
  const left    = total - cash - fonepay - credit;
  document.getElementById('splitRemaining').textContent = fmt(Math.max(left, 0));
  document.getElementById('splitCreditDetails').style.display = credit > 0 ? '' : 'none';
}

async function confirmSplit() {
  if (!state.currentOrder) return;
  const discount = _getCartDiscount();
  const total    = Math.max(parseFloat(state.currentOrder.grand_total) - discount, 0);
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
      body: JSON.stringify({payments, discount})
    });
    state.currentOrder = order;
    bootstrap.Modal.getInstance(document.getElementById('splitModal'))?.hide();
    renderCart();
    loadTables();
    showReceipt(order);
  } catch(e) { showErr(e.message); }
}

// ── Receipt helpers ────────────────────────────────────────────────────────
function _esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function _f2(n) { return parseFloat(n||0).toFixed(2); }

// AD → BS (Bikram Sambat) date conversion
function adToBS(date) {
  const BS_DATA = {
    2074:[31,31,32,31,31,31,30,29,30,29,30,30],
    2075:[31,31,32,32,31,30,30,29,30,29,30,30],
    2076:[31,32,31,32,31,30,30,30,29,29,30,30],
    2077:[31,32,31,32,31,30,30,30,29,29,30,30],
    2078:[31,31,32,32,31,30,30,29,30,29,30,30],
    2079:[31,31,32,31,31,31,30,29,30,29,30,30],
    2080:[31,32,31,32,31,30,30,30,29,30,30,30],
    2081:[31,31,32,32,31,30,30,29,30,29,30,30],
    2082:[31,31,32,31,31,31,30,29,30,29,30,30],
    2083:[31,32,31,31,31,30,30,30,29,29,30,30],
    2084:[31,31,32,32,31,30,30,29,30,29,30,30],
    2085:[31,31,32,31,31,31,30,29,30,29,30,30],
    2086:[31,32,31,32,31,30,30,30,29,30,30,30],
    2087:[31,31,32,32,31,30,30,29,30,29,30,30],
    2088:[31,31,32,31,31,31,30,29,30,29,30,30],
    2089:[31,32,31,31,31,30,30,30,29,29,30,30],
    2090:[31,31,32,31,31,30,30,30,29,30,30,30],
  };
  // Reference: BS 2077 Baisakh 1 = AD 2020 April 13
  const REF_AD  = new Date(2020, 3, 13); // April 13, 2020 (month is 0-indexed)
  const REF_BS  = 2077;
  const MS_DAY  = 86400000;
  let days = Math.round((Date.UTC(date.getFullYear(),date.getMonth(),date.getDate())
                        - Date.UTC(2020,3,13)) / MS_DAY);
  if (days < 0) return null;
  let bsYear = REF_BS;
  while (BS_DATA[bsYear]) {
    const yd = BS_DATA[bsYear].reduce((a,b)=>a+b,0);
    if (days < yd) break;
    days -= yd;
    bsYear++;
  }
  if (!BS_DATA[bsYear]) return null;
  let bsMonth = 1;
  for (let m=0;m<12;m++) {
    if (days < BS_DATA[bsYear][m]) { bsMonth=m+1; break; }
    days -= BS_DATA[bsYear][m];
  }
  return { year:bsYear, month:bsMonth, day:days+1 };
}

// Number → English words (Nepali lakh/crore system)
function numberToWords(num) {
  const ones=['','One','Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten',
    'Eleven','Twelve','Thirteen','Fourteen','Fifteen','Sixteen','Seventeen','Eighteen','Nineteen'];
  const tens=['','','Twenty','Thirty','Forty','Fifty','Sixty','Seventy','Eighty','Ninety'];
  function conv(n) {
    if (n===0) return '';
    if (n<20) return ones[n];
    if (n<100) return tens[Math.floor(n/10)]+(n%10?' '+ones[n%10]:'');
    if (n<1000) return ones[Math.floor(n/100)]+' Hundred'+(n%100?' '+conv(n%100):'');
    if (n<100000) return conv(Math.floor(n/1000))+' Thousand'+(n%1000?' '+conv(n%1000):'');
    if (n<10000000) return conv(Math.floor(n/100000))+' Lakh'+(n%100000?' '+conv(n%100000):'');
    return conv(Math.floor(n/10000000))+' Crore'+(n%10000000?' '+conv(n%10000000):'');
  }
  const n = Math.round(parseFloat(num||0));
  return 'Rs. '+(n===0?'Zero':conv(n))+' Only';
}

// Build complete receipt HTML (used for both modal preview and print popup)
function buildReceiptHTML(order) {
  const now = order.created_at ? new Date(order.created_at) : new Date();
  const adDate = [
    String(now.getDate()).padStart(2,'0'),
    String(now.getMonth()+1).padStart(2,'0'),
    now.getFullYear()
  ].join('/');
  const timeStr = now.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',hour12:true});
  const bs = adToBS(now);
  const bsDate = bs
    ? `${String(bs.day).padStart(2,'0')}/${String(bs.month).padStart(2,'0')}/${bs.year}`
    : '—';

  const discount   = parseFloat(order.discount_amount||0);
  const grandTotal = parseFloat(order.grand_total||0);
  const subtotal   = parseFloat(order.subtotal||0);
  const credits    = order.credit_records||[];

  let payMode   = '—';
  let tender    = grandTotal;
  let change    = 0;
  if ((order.payments||[]).length>0) {
    const ms = order.payments;
    if (ms.length===1) {
      const m = ms[0].method;
      payMode = m==='CASH'?'Cash':m==='CARD'?'Card':m==='FONEPAY'?'QR (FonePay)':
                m==='ESEWA'?'QR (eSewa)':m==='KHALTI'?'QR (Khalti)':m;
      tender  = parseFloat(ms[0].amount||0);
    } else {
      payMode = 'Split';
      tender  = ms.reduce((s,p)=>s+parseFloat(p.amount||0),0);
    }
    change = Math.max(tender-grandTotal,0);
  } else if (credits.length>0) {
    payMode = 'Credit';
    tender  = grandTotal;
  }
  const customerName = credits.length>0 ? credits[0].customer_name : '';
  const tableLabel   = order.table_no || (order.order_type==='TAKEAWAY'?'Takeaway':'—');

  const itemRows = (order.items||[]).map((item,idx)=>`
    <tr>
      <td class="rc-snl">${idx+1}</td>
      <td class="rc-part">
        <div>${_esc(item.product_name.toUpperCase())}</div>
        <div style="font-size:7.5pt;color:#444;">HSC: &nbsp;</div>
      </td>
      <td class="rc-num">${item.qty}</td>
      <td class="rc-num">${_f2(item.unit_price)}</td>
      <td class="rc-num">${_f2(item.line_total)}</td>
    </tr>`).join('');

  return `
<div class="rc-wrap">
  <div class="rc-c rc-b" style="font-size:10.5pt;">Yasumi Restaurant</div>
  <div class="rc-c">Durbarmarg, Kathmandu</div>
  <div class="rc-c">PAN No. : 155481134</div>
  <div class="rc-c">Contact : 015904266</div>
  <div class="rc-dsolid"></div>
  <div class="rc-c rc-b" style="letter-spacing:.5px;">ABBREVIATED TAX INVOICE</div>
  <div class="rc-dsolid"></div>

  <div class="rc-row"><span class="rc-lbl">Bill NO</span>: <b>${_esc(order.order_no)}</b></div>
  <div class="rc-row"><span class="rc-lbl">Date</span>: ${adDate}</div>
  <div class="rc-row"><span class="rc-lbl">Miti</span>: ${bsDate}</div>
  <div class="rc-row"><span class="rc-lbl">Name</span>: ${_esc(customerName)}</div>
  <div class="rc-row"><span class="rc-lbl">Address</span>: </div>
  <div class="rc-row"><span class="rc-lbl">PAN No</span>: </div>
  <div class="rc-row"><span class="rc-lbl">Pay Mode</span>: ${_esc(payMode)}</div>
  <div class="rc-row"><span class="rc-lbl">Table</span>: ${_esc(tableLabel)}</div>
  <div class="rc-row"><span class="rc-lbl">Remarks</span>: </div>

  <div class="rc-dash"></div>

  <table class="rc-tbl">
    <thead>
      <tr>
        <th style="width:20px;text-align:center;">Snl</th>
        <th style="text-align:left;">Particulars</th>
        <th class="rc-num" style="width:28px;">Qty</th>
        <th class="rc-num" style="width:52px;">Rate</th>
        <th class="rc-num" style="width:58px;">Amount</th>
      </tr>
    </thead>
    <tbody>${itemRows}</tbody>
  </table>

  <div class="rc-dash"></div>

  <table class="rc-tots">
    <tr><td class="rc-tl">Gross Amount :</td><td class="rc-tv">${_f2(subtotal)}</td></tr>
    <tr><td class="rc-tl">Discount :</td><td class="rc-tv">${_f2(discount)}</td></tr>
    <tr><td class="rc-tl rc-b">Net Amount :</td><td class="rc-tv rc-b">${_f2(grandTotal)}</td></tr>
    <tr><td colspan="2" style="padding:3px 0;"></td></tr>
    <tr><td class="rc-tl">Tender :</td><td class="rc-tv">${_f2(tender)}</td></tr>
    <tr><td class="rc-tl">Change :</td><td class="rc-tv">${_f2(change)}</td></tr>
  </table>

  <div class="rc-dash"></div>
  <div class="rc-words">${_esc(numberToWords(grandTotal))}</div>
  <div class="rc-dash"></div>

  <div class="rc-c" style="font-size:8pt;padding:3px 2px;line-height:1.45;">
    Win a side dish or chicken/avocado sushi by sharing<br>
    your experience on Google Reviews! Thank you!
  </div>
  <div class="rc-dash"></div>

  <div class="rc-row"><span class="rc-lbl">Counter</span>: ${_esc(payMode)} &nbsp;( ${_esc(timeStr)} )</div>
  <div class="rc-row"><span class="rc-lbl">Cashier</span>: Admin</div>
  <div style="height:10px;"></div>
</div>`;
}

const RECEIPT_CSS = `
  @page { margin: 4mm 3mm; size: 80mm auto; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Courier New',Courier,monospace; font-size:9.5pt; color:#000;
         background:#fff; width:76mm; margin:0 auto; padding:3px 2px;
         -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  .rc-wrap { width:100%; }
  .rc-c    { text-align:center; margin:1px 0; }
  .rc-b    { font-weight:bold; }
  .rc-dsolid { border-top:1.5px solid #000; margin:3px 0; }
  .rc-dash   { border-top:1px dashed #000; margin:4px 0; }
  .rc-row  { font-size:9pt; margin:1.5px 0; }
  .rc-lbl  { display:inline-block; width:82px; }
  .rc-tbl  { width:100%; border-collapse:collapse; font-size:8.5pt; }
  .rc-tbl th { padding:2px 1px; border-bottom:1px dashed #000; font-size:8pt; }
  .rc-tbl td { padding:1.5px 1px; vertical-align:top; }
  .rc-snl  { text-align:center; width:20px; }
  .rc-part { text-align:left; }
  .rc-num  { text-align:right; }
  .rc-tots { width:100%; border-collapse:collapse; font-size:9pt; }
  .rc-tl   { text-align:right; padding-right:5px; }
  .rc-tv   { text-align:right; width:68px; }
  .rc-words { font-size:9pt; margin:2px 0; }
`;

// ── Receipt Print ──────────────────────────────────────────────────────────
function printReceipt() {
  if (!state.lastReceiptOrder) return;
  const body = buildReceiptHTML(state.lastReceiptOrder);
  const win  = window.open('', '_blank', 'width=440,height=720,scrollbars=yes');
  if (!win) { alert('Allow popups to print receipt.'); return; }
  win.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Receipt · Yasumi</title><style>${RECEIPT_CSS}</style></head>
<body>${body}</body></html>`);
  win.document.close();
  win.focus();
  setTimeout(()=>{ win.print(); win.close(); }, 450);
}

// ── Receipt ────────────────────────────────────────────────────────────────
function showReceipt(order) {
  state.lastReceiptOrder = order;
  document.getElementById('receiptBody').innerHTML = buildReceiptHTML(order);
  new bootstrap.Modal(document.getElementById('receiptModal')).show();
}
