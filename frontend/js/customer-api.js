async function request(path, options = {}) {
  const response = await fetch(path, {credentials: 'same-origin', ...options, headers: {'Content-Type': 'application/json', ...(options.headers || {})}});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || 'Please try again in a moment.');
  return body;
}
export const registerCustomer = payload => request('/api/customer/register', {method: 'POST', body: JSON.stringify(payload)});
export const loginCustomer = payload => request('/api/customer/login', {method: 'POST', body: JSON.stringify(payload)});
export const getCustomerSession = () => request('/api/customer/session');
export const logoutCustomer = () => request('/api/customer/logout', {method: 'POST'});
export const sendContactMessage = payload => request('/api/contact', {method: 'POST', body: JSON.stringify(payload)});
