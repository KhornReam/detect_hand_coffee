const KEY='brewco_cart_v1';
export function getCart(){try{return JSON.parse(sessionStorage.getItem(KEY)||'[]')}catch{return []}}
export function saveCart(cart){sessionStorage.setItem(KEY,JSON.stringify(cart));window.dispatchEvent(new Event('cartchange'))}
export function addItem(item){const cart=getCart();const key=JSON.stringify([item.productId,item.options]);const found=cart.find(x=>JSON.stringify([x.productId,x.options])===key);if(found)found.quantity=Math.min(20,found.quantity+item.quantity);else cart.push(item);saveCart(cart)}
export function removeItem(id){saveCart(getCart().filter(x=>x.lineId!==id))}
export function setQuantity(id,n){const cart=getCart();const item=cart.find(x=>x.lineId===id);if(item)item.quantity=Math.max(1,Math.min(20,n));saveCart(cart)}
export function replaceItem(id,item){saveCart(getCart().map(x=>x.lineId===id?item:x))}
export function clearCart(){sessionStorage.removeItem(KEY);window.dispatchEvent(new Event('cartchange'))}
export const subtotal=cart=>Math.round(cart.reduce((s,x)=>s+x.unitPrice*x.quantity,0)*100)/100;
