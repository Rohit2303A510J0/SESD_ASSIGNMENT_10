const API_BASE = 'https://sesd-assignment-10.onrender.com/api';

async function fetchProducts() {
  const res = await fetch(API_BASE + '/products');
  return res.json();
}

async function renderProducts() {
  const prods = await fetchProducts();
  const container = document.getElementById('products');
  if (!container) return;
  container.innerHTML = '';

  prods.forEach(p => {
    const div = document.createElement('div');
    div.className = 'product';
    div.innerHTML = `
      <h3>${p.name}</h3>
      <p>${p.description}</p>
      <p>₹${p.price.toFixed(2)}</p>
      <p>Stock: ${p.inventory}</p>
      <input type='number' min='1' value='1' id='qty-${p.id}'>
      <button data-id='${p.id}'>Add to Cart</button>
    `;
    container.appendChild(div);
  });

  container.querySelectorAll('button[data-id]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-id');
      const qty = parseInt(document.getElementById('qty-' + id).value || '1');
      addToCart({ product_id: parseInt(id), quantity: qty });
      alert('Added to cart ✅');
    });
  });
}

function getCart() {
  return JSON.parse(localStorage.getItem('cart') || '[]');
}

function saveCart(cart) {
  localStorage.setItem('cart', JSON.stringify(cart));
}

function addToCart(item) {
  const cart = getCart();
  const found = cart.find(i => i.product_id === item.product_id);
  if (found) found.quantity += item.quantity;
  else cart.push(item);
  saveCart(cart);
}

async function renderCart() {
  const container = document.getElementById('cart');
  if (!container) return;
  const cart = getCart();
  if (cart.length === 0) {
    container.innerText = 'Cart is empty ❗';
  } else {
    const prods = await fetchProducts();
    container.innerHTML = cart.map(it => {
      const p = prods.find(x => x.id === it.product_id) || { name: 'Unknown', price: 0 };
      return `<div>${p.name} — Qty: ${it.quantity} — ₹${(p.price * it.quantity).toFixed(2)}</div>`;
    }).join('');
    document.getElementById('placeOrder')?.addEventListener('click', placeOrder);
  }
}

async function placeOrder() {
  const cart = getCart();
  if (cart.length === 0) return alert('Cart is empty');

  const res = await fetch(API_BASE + '/order', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items: cart })
  });

  const data = await res.json();
  if (!res.ok) return alert('Order Error: ' + (data.error || JSON.stringify(data)));

  await fetch(API_BASE + '/payment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ order_id: data.order_id })
  });

  localStorage.removeItem('cart');
  document.getElementById('orderResult').innerText =
    '✅ Order placed! Your Order ID: ' + data.order_id;
}

async function trackOrder() {
  const id = parseInt(document.getElementById('orderIdInput').value);
  if (!id) return alert('Enter Order ID');

  const res = await fetch(API_BASE + '/track/' + id);
  const data = await res.json();
  document.getElementById('trackResult').innerText = JSON.stringify(data, null, 2);
}

window.addEventListener('load', () => {
  renderProducts();
  renderCart();
  document.getElementById('trackBtn')?.addEventListener('click', trackOrder);
});
