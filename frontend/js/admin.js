export async function loginAdmin(email,password){const r=await fetch('/api/admin/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})});if(!r.ok){const body=await r.json().catch(()=>({}));throw new Error(body.detail||'Unable to sign in')}return r.json()}
export async function getAdminSession(){const r=await fetch('/api/admin/session',{credentials:'same-origin'});if(!r.ok)throw new Error('Admin login required');return r.json()}
export async function logoutAdmin(){await fetch('/api/admin/logout',{method:'POST',credentials:'same-origin'})}

async function adminRequest(path,options={}){
  const response=await fetch(path,{credentials:'same-origin',...options,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(options.headers||{})}});
  const payload=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(payload.detail||'The admin change could not be saved');
  return payload;
}
export const getAdminMenu=()=>adminRequest('/api/admin/menu');
export const saveAdminMenu=menu=>adminRequest('/api/admin/menu',{method:'PUT',body:JSON.stringify(menu)});
export const getAdminContact=()=>adminRequest('/api/admin/contact');
export const saveAdminContact=contact=>adminRequest('/api/admin/contact',{method:'PUT',body:JSON.stringify(contact)});
export const getAdminUsers=()=>adminRequest('/api/admin/users');
export const getAdminMessages=()=>adminRequest('/api/admin/messages');
export const saveAdminUser=(user,id)=>adminRequest(id?`/api/admin/users/${encodeURIComponent(id)}`:'/api/admin/users',{method:id?'PUT':'POST',body:JSON.stringify(user)});
export const deleteAdminUser=id=>adminRequest(`/api/admin/users/${encodeURIComponent(id)}`,{method:'DELETE'});
