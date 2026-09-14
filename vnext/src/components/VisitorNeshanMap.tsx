import { useEffect, useMemo, useRef, useState } from 'react'
import { getNeshanMapConfig, getRouteMapLeg, getRouteMapPlan, type NeshanRouteMapPlanResponse } from '../api/neginApi'

type Props={routeId:string|null;mode:'sales'|'shortest';selectedCustomerId:string;recenterNonce:number;onSelectCustomer:(id:string)=>void;onPrimaryCustomer:(id:string)=>void;onNotice:(m:string)=>void;onOrderChange:(ids:string[])=>void}
type Pos={latitude:number;longitude:number;accuracy?:number;heading?:number|null}
type ML={Map:new(o:Record<string,unknown>)=>any;Marker:new(o?:Record<string,unknown>)=>any;NavigationControl:new()=>unknown}
const CSS='https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.css'
const JS='https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.umd.js'
const STYLE='https://static.neshan.org/sdk/maplibre/styles/light.json'

function fromWindow(){const v=(window as unknown as{maplibregl?:ML&{default?:ML}}).maplibregl;return v?.default??v??null}
let proxiedStylePromise:Promise<any>|null=null
let proxiedStyleKey=''
function loadProxiedStyle(key:string){
  if(proxiedStylePromise&&proxiedStyleKey===key)return proxiedStylePromise
  proxiedStyleKey=key
  proxiedStylePromise=fetch(STYLE,{cache:'force-cache'}).then(async response=>{
    if(!response.ok)throw new Error('Neshan map style unavailable')
    const style=await response.json() as {sources?:Record<string,{tiles?:string[]}>}
    const prefix='nsh://api.neshan.org/'
    Object.values(style.sources??{}).forEach(source=>{
      if(!Array.isArray(source.tiles))return
      source.tiles=source.tiles.map(url=>{
        if(!url.startsWith(prefix))return url
        const rest=url.slice(prefix.length)
        const sep=rest.includes('?')?'&':'?'
        return '/neshan-basemap/'+rest+sep+'key='+encodeURIComponent(key)
      })
    })
    return style
  }).catch(error=>{proxiedStylePromise=null;proxiedStyleKey='';throw error})
  return proxiedStylePromise
}
async function loadSdk():Promise<ML>{
  const old=fromWindow();if(old)return old
  if(!document.querySelector(`link[href="${CSS}"]`)){const l=document.createElement('link');l.rel='stylesheet';l.href=CSS;document.head.appendChild(l)}
  let s=document.querySelector<HTMLScriptElement>(`script[src="${JS}"]`)
  if(!s){s=document.createElement('script');s.src=JS;s.defer=true;document.head.appendChild(s)}
  return new Promise((resolve,reject)=>{
    const ready=()=>{const v=fromWindow();v?resolve(v):reject(new Error('Neshan MapLibre SDK unavailable'))}
    s?.addEventListener('load',ready,{once:true});s?.addEventListener('error',()=>reject(new Error('Neshan MapLibre SDK failed to load')),{once:true})
  })
}
function geo():Promise<Pos|null>{
  if(!navigator.geolocation)return Promise.resolve(null)
  return new Promise(r=>navigator.geolocation.getCurrentPosition(p=>r({latitude:p.coords.latitude,longitude:p.coords.longitude,accuracy:p.coords.accuracy,heading:p.coords.heading}),()=>r(null),{enableHighAccuracy:true,maximumAge:15000,timeout:15000}))
}
function decode(s:string){const out:Array<[number,number]>=[];let i=0,lat=0,lng=0;while(i<s.length){let sh=0,r=0,b=0;do{b=s.charCodeAt(i++)-63;r|=(b&31)<<sh;sh+=5}while(b>=32);lat+=r&1?~(r>>1):r>>1;sh=0;r=0;do{b=s.charCodeAt(i++)-63;r|=(b&31)<<sh;sh+=5}while(b>=32);lng+=r&1?~(r>>1):r>>1;out.push([lng/1e5,lat/1e5])}return out}
const ROUTE_CLUSTER_RADIUS_KM=200
const MAX_ROUTE_GPS_DISTANCE_KM=200
function distanceKm(a:Pos,b:{latitude:number;longitude:number}){const r=6371,toRad=(v:number)=>v*Math.PI/180,dLat=toRad(b.latitude-a.latitude),dLon=toRad(b.longitude-a.longitude),la1=toRad(a.latitude),la2=toRad(b.latitude);const h=Math.sin(dLat/2)**2+Math.cos(la1)*Math.cos(la2)*Math.sin(dLon/2)**2;return 2*r*Math.asin(Math.min(1,Math.sqrt(h)))}
function routeCluster(plan:NeshanRouteMapPlanResponse){const located=plan.ordered_customers.filter(c=>c.latitude!=null&&c.longitude!=null);if(located.length<=2)return located;let best=located;let bestCount=0;for(const anchor of located){const origin={latitude:Number(anchor.latitude),longitude:Number(anchor.longitude)};const near=located.filter(c=>distanceKm(origin,{latitude:Number(c.latitude),longitude:Number(c.longitude)})<=ROUTE_CLUSTER_RADIUS_KM);if(near.length>bestCount){best=near;bestCount=near.length}}return bestCount>=Math.max(2,Math.ceil(located.length*.5))?best:located}
function gpsMatchesPlan(p:Pos,plan:NeshanRouteMapPlanResponse){return routeCluster(plan).some(c=>distanceKm(p,{latitude:Number(c.latitude),longitude:Number(c.longitude)})<=MAX_ROUTE_GPS_DISTANCE_KM)}

function draw(map:any,encoded:string){
  if(!map?.isStyleLoaded())return
  for(const id of ['v017-route-highlight','v017-route','v017-route-casing','v017-route-glow'])if(map.getLayer(id))map.removeLayer(id)
  if(map.getSource('v017-route'))map.removeSource('v017-route')
  const c=decode(encoded);if(c.length<2)return
  map.addSource('v017-route',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:c}}})
  const layout={'line-cap':'round','line-join':'round'}
  map.addLayer({id:'v017-route-glow',type:'line',source:'v017-route',layout,paint:{'line-color':'#48c6ff','line-width':8.5,'line-opacity':.18,'line-blur':1.8}})
  map.addLayer({id:'v017-route-casing',type:'line',source:'v017-route',layout,paint:{'line-color':'#071827','line-width':6.2,'line-opacity':.88}})
  map.addLayer({id:'v017-route',type:'line',source:'v017-route',layout,paint:{'line-color':'#46c8ff','line-width':4,'line-opacity':.98}})
  map.addLayer({id:'v017-route-highlight',type:'line',source:'v017-route',layout,paint:{'line-color':'#e5f8ff','line-width':1.1,'line-opacity':.72}})
}
function focusPolyline(map:any,encoded:string){const c=decode(encoded);if(!map||c.length<2)return;const lngs=c.map(([lng])=>lng),lats=c.map(([,lat])=>lat);map.fitBounds([[Math.min(...lngs),Math.min(...lats)],[Math.max(...lngs),Math.max(...lats)]],{padding:{top:86,right:52,bottom:126,left:52},maxZoom:16,duration:700,essential:true})}

export function VisitorNeshanMap({routeId,mode,selectedCustomerId,recenterNonce,onSelectCustomer,onPrimaryCustomer,onNotice,onOrderChange}:Props){
  const shell=useRef<HTMLDivElement|null>(null),host=useRef<HTMLDivElement|null>(null),map=useRef<any>(null),markers=useRef<any[]>([]),sdkRef=useRef<ML|null>(null)
  const selectedIdRef=useRef(selectedCustomerId),selectCustomerRef=useRef(onSelectCustomer),primaryCustomerRef=useRef(onPrimaryCustomer),orderChangeRef=useRef(onOrderChange)
  const trustedCustomersRef=useRef<NeshanRouteMapPlanResponse['ordered_customers']>([]),trustedPosRef=useRef<Pos|null>(null),polyRef=useRef('')
  const keyRef=useRef(''),focusTokenRef=useRef(''),routeRequestRef=useRef(null as any),routeFocusKeyRef=useRef(''),needsRecoveryRef=useRef(false),retryAttemptRef=useRef(0),retryTimerRef=useRef(null as any)
  selectedIdRef.current=selectedCustomerId;selectCustomerRef.current=onSelectCustomer;primaryCustomerRef.current=onPrimaryCustomer;orderChangeRef.current=onOrderChange
  const [plan,setPlan]=useState<NeshanRouteMapPlanResponse|null>(null),[key,setKey]=useState(''),[pos,setPos]=useState<Pos|null>(null),[leg,setLeg]=useState(''),[error,setError]=useState(''),[mapReady,setMapReady]=useState(false),[initNonce,setInitNonce]=useState(0),[fullscreen,setFullscreen]=useState(false)
  const trustedCustomers=useMemo(()=>plan?routeCluster(plan):[],[plan])
  const trustedPos=useMemo(()=>pos&&plan&&String(plan.route.id)===String(routeId)&&gpsMatchesPlan(pos,plan)?pos:null,[pos,plan,routeId])
  const backendFirst=plan?.ordered_customers.find(c=>c.latitude!=null&&c.longitude!=null)??null
  const trustedFirst=trustedCustomers[0]??null
  const poly=leg||(trustedPos&&backendFirst&&trustedFirst&&String(backendFirst.id)===String(trustedFirst.id)&&String(selectedCustomerId)===String(trustedFirst.id)?plan?.polyline||'':'')
  const selected=useMemo(()=>trustedCustomers.find(c=>String(c.id)===selectedCustomerId)??null,[trustedCustomers,selectedCustomerId])
  const selectedPlanCustomer=useMemo(()=>plan?.ordered_customers.find(c=>String(c.id)===selectedCustomerId)??plan?.unlocated_customers.find(c=>String(c.id)===selectedCustomerId)??null,[plan,selectedCustomerId])
  const modeLabel=mode==='sales'?'\u0627\u0648\u0644\u0648\u06cc\u062a \u0641\u0631\u0648\u0634':'\u06a9\u0648\u062a\u0627\u0647\u200c\u062a\u0631\u06cc\u0646 \u0645\u0633\u06cc\u0631'
  const locatedCount=plan?.ordered_customers.filter(c=>c.latitude!=null&&c.longitude!=null).length??0
  const missingCount=plan?.missing_location_count??0
  trustedCustomersRef.current=trustedCustomers;trustedPosRef.current=trustedPos;polyRef.current=poly;keyRef.current=key

  useEffect(()=>{if(!routeId||pos||!navigator.geolocation||!navigator.permissions)return;let off=false
    void navigator.permissions.query({name:'geolocation'}).then(status=>{if(off||status.state!=='granted')return;return geo().then(p=>{if(!off&&p)setPos(p)})}).catch(()=>undefined)
    return()=>{off=true}
  },[routeId,pos])

  useEffect(()=>{if(!routeId||!navigator.geolocation)return;let dead=false
    const watchId=navigator.geolocation.watchPosition(position=>{if(dead)return;const next:Pos={latitude:position.coords.latitude,longitude:position.coords.longitude,accuracy:position.coords.accuracy,heading:position.coords.heading};setPos(current=>!current||distanceKm(current,next)*1000>=5?next:current)},()=>undefined,{enableHighAccuracy:true,maximumAge:5000,timeout:20000})
    return()=>{dead=true;navigator.geolocation.clearWatch(watchId)}
  },[routeId])

  useEffect(()=>{const onFullscreen=()=>{setFullscreen(document.fullscreenElement===shell.current);window.setTimeout(()=>map.current?.resize?.(),80)};document.addEventListener('fullscreenchange',onFullscreen);return()=>document.removeEventListener('fullscreenchange',onFullscreen)},[])

  useEffect(()=>{if(!routeId)return;let off=false;setError('');setLeg('')
    void Promise.all([getNeshanMapConfig(),getRouteMapPlan(routeId,mode==='sales'?'sales_priority':'shortest',trustedPos)])
      .then(([c,p])=>{if(!off){setKey(c.api_key ?? '');setPlan(p);orderChangeRef.current([...p.ordered_customers,...p.unlocated_customers].map(customer=>String(customer.id)));const first=routeCluster(p)[0];if(first)primaryCustomerRef.current(String(first.id))}}).catch(e=>{if(!off)setError(e instanceof Error?e.message:'Neshan map unavailable')})
    return()=>{off=true}
  },[routeId,mode,trustedPos])

  useEffect(()=>{if(!key||!host.current||map.current)return;let dead=false,local:any=null,observer:ResizeObserver|null=null
    void loadSdk().then(sdk=>{if(dead||!host.current||map.current)return
      const first=trustedCustomersRef.current[0],initialPos=trustedPosRef.current
      local=new sdk.Map({container:host.current,style:STYLE,center:initialPos?[initialPos.longitude,initialPos.latitude]:first?[Number(first.longitude),Number(first.latitude)]:[51.4,35.7],zoom:initialPos?13:10,apiKey:key,rtl:{lazy:false}})
      sdkRef.current=sdk;map.current=local
      observer=new ResizeObserver(()=>{if(!dead)window.requestAnimationFrame(()=>local?.resize?.())});observer.observe(host.current)
      local.on('error',(event:any)=>{if(dead)return;const message=String(event?.error?.message||'Neshan map rendering failed');if(!/tile request failed/i.test(message))needsRecoveryRef.current=true;console.warn('[Neshan map]',message)})
      local.on('load',()=>{if(dead)return;retryAttemptRef.current=0;needsRecoveryRef.current=false;setError('');setMapReady(true);window.requestAnimationFrame(()=>local?.resize?.())})
    }).catch(e=>{if(dead)return;map.current=null;sdkRef.current=null;setMapReady(false);setError(e instanceof Error?e.message:'Neshan SDK unavailable');retryAttemptRef.current+=1
      if(navigator.onLine){const delay=Math.min(15000,1000*(2**Math.min(retryAttemptRef.current,4)));if(retryTimerRef.current)window.clearTimeout(retryTimerRef.current);retryTimerRef.current=window.setTimeout(()=>setInitNonce(value=>value+1),delay)}
    })
    return()=>{dead=true;observer?.disconnect();if(retryTimerRef.current){window.clearTimeout(retryTimerRef.current);retryTimerRef.current=null}if(local&&map.current===local){local.remove();map.current=null;sdkRef.current=null;setMapReady(false)}}
  },[key,initNonce])

  useEffect(()=>{if(!mapReady||!map.current||!sdkRef.current)return;const current=map.current,sdk=sdkRef.current
    markers.current.forEach(marker=>marker.remove());markers.current=[]
    trustedCustomers.forEach((customer,index)=>{const el=document.createElement('button');el.type='button';const tier=String(customer.priority_tier||'').toLowerCase().replace(/[^a-z0-9_-]/g,'');el.className='vr-map-live-marker'+(tier?' tier-'+tier:'')+(String(customer.id)===selectedIdRef.current?' selected':'');el.textContent=String(index+1);el.setAttribute('aria-label',String(customer.name||('Customer '+(index+1))));el.setAttribute('aria-pressed',String(String(customer.id)===selectedIdRef.current));el.dataset.customerId=String(customer.id);el.onclick=()=>selectCustomerRef.current(String(customer.id));markers.current.push(new sdk.Marker({element:el,anchor:'bottom'}).setLngLat([Number(customer.longitude),Number(customer.latitude)]).addTo(current))})
    if(trustedPos){const el=document.createElement('span');el.className='vr-map-live-seller';markers.current.push(new sdk.Marker({element:el}).setLngLat([trustedPos.longitude,trustedPos.latitude]).addTo(current))}
  },[mapReady,trustedCustomers,trustedPos])

  useEffect(()=>{if(!host.current)return;host.current.querySelectorAll<HTMLElement>('.vr-map-live-marker').forEach(el=>{const selectedNow=el.dataset.customerId===selectedCustomerId;el.classList.toggle('selected',selectedNow);el.setAttribute('aria-pressed',String(selectedNow))})},[selectedCustomerId,mapReady,trustedCustomers])

  useEffect(()=>{if(!mapReady||!map.current)return;const first=trustedCustomers[0]??plan?.ordered_customers.find(c=>c.latitude!=null&&c.longitude!=null),focus=plan?.ordered_customers.find(c=>String(c.id)===selectedCustomerId&&c.latitude!=null&&c.longitude!=null)??first;if(!focus)return
    const token=`${routeId??''}|${mode}|${selectedCustomerId}`;if(focusTokenRef.current===token)return;focusTokenRef.current=token
    map.current.easeTo({center:[Number(focus.longitude),Number(focus.latitude)],zoom:15,duration:550,essential:true})
  },[mapReady,routeId,mode,selectedCustomerId,trustedCustomers,plan])

  useEffect(()=>{const recover=()=>{if(document.visibilityState==='hidden')return;const current=map.current
      if(!current){setInitNonce(value=>value+1);return}
      current.resize?.();current.triggerRepaint?.()
      if(!needsRecoveryRef.current||!navigator.onLine||!keyRef.current)return
      const center=current.getCenter?.(),zoom=current.getZoom?.(),bearing=current.getBearing?.(),pitch=current.getPitch?.()
      void loadProxiedStyle(keyRef.current).then(style=>{if(map.current!==current)return;current.setStyle?.(style);current.once?.('styledata',()=>{if(map.current!==current)return;needsRecoveryRef.current=false;if(center)current.jumpTo?.({center:[center.lng,center.lat],zoom,bearing,pitch});draw(current,polyRef.current)})}).catch(()=>undefined)
    }
    const onVisible=()=>{if(document.visibilityState==='visible')window.setTimeout(recover,120)}
    window.addEventListener('online',recover);document.addEventListener('visibilitychange',onVisible)
    return()=>{window.removeEventListener('online',recover);document.removeEventListener('visibilitychange',onVisible)}
  },[])

  useEffect(()=>{if(mapReady)draw(map.current,poly)},[poly,mapReady])
  useEffect(()=>{if(!routeId||!trustedPos||!selected){setLeg('');routeRequestRef.current=null;return}const key=`${routeId}:${selected.id}`,previous=routeRequestRef.current,moved=previous?distanceKm(previous.position,trustedPos)*1000:Infinity,elapsed=previous?Date.now()-previous.at:Infinity;if(previous?.key===key&&moved<35&&elapsed<20000)return;let off=false;const shouldFocus=routeFocusKeyRef.current!==key;routeRequestRef.current={key,position:trustedPos,at:Date.now()};void getRouteMapLeg(routeId,String(selected.id),trustedPos).then(r=>{if(off)return;const next=r.polyline||'';setLeg(next);if(next&&shouldFocus){routeFocusKeyRef.current=key;window.setTimeout(()=>focusPolyline(map.current,next),0)}}).catch(e=>{if(!off)onNotice(e instanceof Error?e.message:'Live route unavailable')});return()=>{off=true}},[routeId,trustedPos,selected,onNotice])
  useEffect(()=>{if(!recenterNonce)return;let off=false;void geo().then(p=>{if(off)return;if(!p){onNotice('\u062f\u0633\u062a\u0631\u0633\u06cc GPS \u0628\u0631\u0642\u0631\u0627\u0631 \u0646\u06cc\u0633\u062a \u06cc\u0627 \u0645\u0648\u0642\u0639\u06cc\u062a \u062f\u0631\u06cc\u0627\u0641\u062a \u0646\u0634\u062f.');return}setPos(p);if(!plan||gpsMatchesPlan(p,plan)){map.current?.flyTo({center:[p.longitude,p.latitude],zoom:14,duration:650,essential:true})}else{onNotice('\u0645\u0648\u0642\u0639\u06cc\u062a GPS \u0628\u0627 \u0645\u062d\u062f\u0648\u062f\u0647 \u0645\u0633\u06cc\u0631 \u0627\u0646\u062a\u062e\u0627\u0628\u200c\u0634\u062f\u0647 \u0647\u0645\u062e\u0648\u0627\u0646 \u0646\u06cc\u0633\u062a \u0648 \u0646\u0627\u062f\u06cc\u062f\u0647 \u06af\u0631\u0641\u062a\u0647 \u0634\u062f.')}});return()=>{off=true}},[recenterNonce,onNotice,plan])

  function fitRouteView(){const points=(plan?.ordered_customers??[]).filter(c=>c.latitude!=null&&c.longitude!=null);if(!points.length||!map.current)return;const lngs=points.map(c=>Number(c.longitude)),lats=points.map(c=>Number(c.latitude));map.current.fitBounds([[Math.min(...lngs),Math.min(...lats)],[Math.max(...lngs),Math.max(...lats)]],{padding:{top:96,right:52,bottom:128,left:52},maxZoom:15,duration:650})}
  async function toggleFullscreen(){const target=shell.current;if(!target)return;if(document.fullscreenElement){await document.exitFullscreen?.();return}await target.requestFullscreen?.()}
  function centerOnMe(){void geo().then(p=>{if(!p){onNotice('\u062f\u0633\u062a\u0631\u0633\u06cc GPS \u0628\u0631\u0642\u0631\u0627\u0631 \u0646\u06cc\u0633\u062a.');return}setPos(p);if(plan){if(!gpsMatchesPlan(p,plan)){onNotice('\u0645\u0648\u0642\u0639\u06cc\u062a GPS \u0628\u0627 \u0645\u0633\u06cc\u0631 \u0627\u0646\u062a\u062e\u0627\u0628\u200c\u0634\u062f\u0647 \u0647\u0645\u062e\u0648\u0627\u0646 \u0646\u06cc\u0633\u062a.');return}}map.current?.flyTo({center:[p.longitude,p.latitude],zoom:14,duration:650,essential:true})})}

  return <div ref={shell} className={'vr-map-live-shell'+(fullscreen?' is-fullscreen':'')}>
    <div ref={host} className="vr-map-live" aria-label={'\u0646\u0642\u0634\u0647 \u0632\u0646\u062f\u0647 \u0645\u0633\u06cc\u0631 \u0641\u0631\u0648\u0634'}/>
    <details className="vr-map-mobile-tools">
      <summary aria-label={'\u0644\u0627\u06cc\u0647\u200c\u0647\u0627 \u0648 \u062a\u062d\u0644\u06cc\u0644 \u0646\u0642\u0634\u0647'}><span aria-hidden="true">{'\u2630'}</span><b>{'\u0644\u0627\u06cc\u0647\u200c\u0647\u0627'}</b></summary>
      <div className="vr-map-mobile-tools-panel">
        <div className="vr-map-hud"><span className="vr-map-mode-chip">{modeLabel}</span><span>{locatedCount} {'\u0645\u0634\u062a\u0631\u06cc \u0631\u0648\u06cc \u0646\u0642\u0634\u0647'}</span>{missingCount>0?<span className="warning">{missingCount} {'\u0628\u062f\u0648\u0646 \u0644\u0648\u06a9\u06cc\u0634\u0646'}</span>:null}</div>
        {selectedPlanCustomer?<div className="vr-map-selected-card"><div><strong>{selectedPlanCustomer.store_name||selectedPlanCustomer.name}</strong><span>{selectedPlanCustomer.address||selectedPlanCustomer.name}</span></div><div className="vr-map-selected-metrics"><span>{'\u0627\u0648\u0644\u0648\u06cc\u062a'} <b>{selectedPlanCustomer.priority_tier||'--'}</b></span><span>{'\u0627\u0645\u062a\u06cc\u0627\u0632'} <b>{Number(selectedPlanCustomer.visit_score||0).toLocaleString('fa-IR')}</b></span></div></div>:null}
      </div>
    </details>
    <div className="vr-map-quick-actions" aria-label={'\u06a9\u0646\u062a\u0631\u0644\u200c\u0647\u0627\u06cc \u0633\u0631\u06cc\u0639 \u0646\u0642\u0634\u0647'}><button type="button" onClick={centerOnMe} aria-label={'\u0645\u0631\u06a9\u0632 \u0631\u0648\u06cc \u0645\u0646'}><b>{'\u25ce'}</b></button><button type="button" onClick={fitRouteView} aria-label={'\u0646\u0645\u0627\u06cc\u0634 \u06a9\u0644 \u0645\u0633\u06cc\u0631'}><b>{'\u2317'}</b></button><button type="button" onClick={()=>void toggleFullscreen()} aria-label={'\u0646\u0642\u0634\u0647 \u062a\u0645\u0627\u0645 \u0635\u0641\u062d\u0647'}><b>{fullscreen?'\u2715':'\u26f6'}</b></button></div>
    <details className="vr-map-fullscreen-customers">
      <summary aria-label={'فهرست مشتریان'}><span aria-hidden="true">{'☷'}</span><b>{locatedCount}</b></summary>
      <div className="vr-map-fullscreen-customers-panel" dir="rtl">
        <div className="vr-map-fullscreen-customers-head"><strong>مشتریان مسیر</strong><span>{locatedCount} مشتری</span></div>
        <div className="vr-map-fullscreen-customers-list">{(plan?.ordered_customers??[]).map((customer,index)=><button type="button" key={String(customer.id)} className={String(customer.id)===selectedCustomerId?'selected':''} onClick={(event)=>{selectCustomerRef.current(String(customer.id));(event.currentTarget.closest('details') as HTMLDetailsElement|null)?.removeAttribute('open')}}><i>{index+1}</i><span><strong>{customer.store_name||customer.name}</strong><small>{customer.address||customer.name}</small></span><em>{customer.priority_tier||'--'}</em></button>)}</div>
      </div>
    </details>
    {!plan&&!error?<span className="vr-map-live-state">{'\u062f\u0631 \u062d\u0627\u0644 \u0628\u0627\u0631\u06af\u0630\u0627\u0631\u06cc \u0646\u0642\u0634\u0647\u2026'}</span>:null}{error?<button type="button" className="vr-map-live-state error" onClick={()=>onNotice(error)}>{'\u0646\u0642\u0634\u0647 \u062f\u0631 \u062f\u0633\u062a\u0631\u0633 \u0646\u06cc\u0633\u062a'}</button>:null}
  </div>
}





