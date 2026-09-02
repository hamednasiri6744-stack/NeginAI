const CACHE='neginai-shell-v214';
const CATALOG_CACHE='neginai-catalog-images-v1';
const SHELL=['/assistant','/planning','/control','/static/assistant.css?v=106','/static/previsit-workspace.css?v=50','/static/assistant.js?v=213','/static/planning.css?v=1','/static/planning.js?v=1','/static/control.css?v=4','/static/control.js?v=4','/static/manifest.webmanifest','/static/negin-brand-icon-192.png','/static/negin-brand-icon-512.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE&&key!==CATALOG_CACHE).map(key=>caches.delete(key)))).then(()=>clients.claim())));
self.addEventListener('fetch',event=>{
  const path=new URL(event.request.url).pathname;
  if(event.request.method!=='GET'||path.startsWith('/chat')||path.startsWith('/control/api/'))return;
  if(path.startsWith('/seller-workspace/previsit/catalog-images/')){
    event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request).then(response=>{if(response.ok)caches.open(CATALOG_CACHE).then(cache=>cache.put(event.request,response.clone()));return response})));
    return;
  }
  event.respondWith(fetch(event.request).catch(()=>caches.match(event.request)));
});
self.addEventListener('push',event=>{
  let data={};
  try{data=event.data?.json()||{}}catch{data={body:event.data?.text()||''}}
  event.waitUntil(self.registration.showNotification(data.title||'نگین پخش',{
    body:data.body||'گزارش خودکار آماده است.',
    icon:'/static/negin-brand-icon-192.png',
    badge:'/static/negin-brand-icon-192.png',
    tag:data.tag||'neginai-automation',
    data:{url:data.url||'/assistant'},
    dir:'rtl',
    lang:'fa',
    renotify:true,
  }));
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  const targetUrl=new URL(event.notification.data?.url||'/assistant',self.location.origin);
  const target=targetUrl.href;
  if(targetUrl.origin!==self.location.origin){
    event.waitUntil(clients.openWindow(target));
    return;
  }
  event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(windows=>{
    const existing=windows.find(client=>client.url.startsWith(self.location.origin));
    if(existing){existing.navigate(target);return existing.focus()}
    return clients.openWindow(target);
  }));
});
