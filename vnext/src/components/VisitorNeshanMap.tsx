import { useEffect, useMemo, useRef, useState } from 'react'
import { getNeshanMapConfig, getRouteMapLeg, getRouteMapPlan, type NeshanRouteMapPlanResponse } from '../api/neginApi'

type Props={routeId:string|null;mode:'sales'|'shortest';selectedCustomerId:string;recenterNonce:number;onSelectCustomer:(id:string)=>void;onPrimaryCustomer:(id:string)=>void;onNotice:(m:string)=>void}
type Pos={latitude:number;longitude:number}
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
  return new Promise(r=>navigator.geolocation.getCurrentPosition(p=>r({latitude:p.coords.latitude,longitude:p.coords.longitude}),()=>r(null),{enableHighAccuracy:true,maximumAge:15000,timeout:15000}))
}
function decode(s:string){const out:Array<[number,number]>=[];let i=0,lat=0,lng=0;while(i<s.length){let sh=0,r=0,b=0;do{b=s.charCodeAt(i++)-63;r|=(b&31)<<sh;sh+=5}while(b>=32);lat+=r&1?~(r>>1):r>>1;sh=0;r=0;do{b=s.charCodeAt(i++)-63;r|=(b&31)<<sh;sh+=5}while(b>=32);lng+=r&1?~(r>>1):r>>1;out.push([lng/1e5,lat/1e5])}return out}
const ROUTE_CLUSTER_RADIUS_KM=200
const MAX_ROUTE_GPS_DISTANCE_KM=200
function distanceKm(a:Pos,b:{latitude:number;longitude:number}){const r=6371,toRad=(v:number)=>v*Math.PI/180,dLat=toRad(b.latitude-a.latitude),dLon=toRad(b.longitude-a.longitude),la1=toRad(a.latitude),la2=toRad(b.latitude);const h=Math.sin(dLat/2)**2+Math.cos(la1)*Math.cos(la2)*Math.sin(dLon/2)**2;return 2*r*Math.asin(Math.min(1,Math.sqrt(h)))}
function routeCluster(plan:NeshanRouteMapPlanResponse){const located=plan.ordered_customers.filter(c=>c.latitude!=null&&c.longitude!=null);if(located.length<=2)return located;let best=located;let bestCount=0;for(const anchor of located){const origin={latitude:Number(anchor.latitude),longitude:Number(anchor.longitude)};const near=located.filter(c=>distanceKm(origin,{latitude:Number(c.latitude),longitude:Number(c.longitude)})<=ROUTE_CLUSTER_RADIUS_KM);if(near.length>bestCount){best=near;bestCount=near.length}}return bestCount>=Math.max(2,Math.ceil(located.length*.5))?best:located}
function gpsMatchesPlan(p:Pos,plan:NeshanRouteMapPlanResponse){return routeCluster(plan).some(c=>distanceKm(p,{latitude:Number(c.latitude),longitude:Number(c.longitude)})<=MAX_ROUTE_GPS_DISTANCE_KM)}

function draw(map:any,encoded:string){
  if(!map?.isStyleLoaded())return
  if(map.getLayer('v017-route'))map.removeLayer('v017-route')
  if(map.getSource('v017-route'))map.removeSource('v017-route')
  const c=decode(encoded);if(c.length<2)return
  map.addSource('v017-route',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:c}}})
  map.addLayer({id:'v017-route',type:'line',source:'v017-route',paint:{'line-color':'#e8b64f','line-width':5,'line-opacity':.9}})
}

export function VisitorNeshanMap({routeId,mode,selectedCustomerId,recenterNonce,onSelectCustomer,onPrimaryCustomer,onNotice}:Props){
  const host=useRef<HTMLDivElement|null>(null),map=useRef<any>(null),markers=useRef<any[]>([]),sdkRef=useRef<ML|null>(null)
  const selectedIdRef=useRef(selectedCustomerId),selectCustomerRef=useRef(onSelectCustomer),primaryCustomerRef=useRef(onPrimaryCustomer)
  const trustedCustomersRef=useRef<NeshanRouteMapPlanResponse['ordered_customers']>([]),trustedPosRef=useRef<Pos|null>(null),polyRef=useRef('')
  const keyRef=useRef(''),focusTokenRef=useRef(''),needsRecoveryRef=useRef(false),retryAttemptRef=useRef(0),retryTimerRef=useRef<number|null>(null)
  selectedIdRef.current=selectedCustomerId;selectCustomerRef.current=onSelectCustomer;primaryCustomerRef.current=onPrimaryCustomer
  const [plan,setPlan]=useState<NeshanRouteMapPlanResponse|null>(null),[key,setKey]=useState(''),[pos,setPos]=useState<Pos|null>(null),[leg,setLeg]=useState(''),[error,setError]=useState(''),[mapReady,setMapReady]=useState(false),[initNonce,setInitNonce]=useState(0)
  const trustedCustomers=useMemo(()=>plan?routeCluster(plan):[],[plan])
  const trustedPos=useMemo(()=>pos&&plan&&String(plan.route.id)===String(routeId)&&gpsMatchesPlan(pos,plan)?pos:null,[pos,plan,routeId])
  const backendFirst=plan?.ordered_customers.find(c=>c.latitude!=null&&c.longitude!=null)??null
  const trustedFirst=trustedCustomers[0]??null
  const poly=leg||(trustedPos&&backendFirst&&trustedFirst&&String(backendFirst.id)===String(trustedFirst.id)&&String(selectedCustomerId)===String(trustedFirst.id)?plan?.polyline||'':'')
  const selected=useMemo(()=>trustedCustomers.find(c=>String(c.id)===selectedCustomerId)??null,[trustedCustomers,selectedCustomerId])
  trustedCustomersRef.current=trustedCustomers;trustedPosRef.current=trustedPos;polyRef.current=poly;keyRef.current=key

  useEffect(()=>{if(!routeId||pos||!navigator.geolocation||!navigator.permissions)return;let off=false
    void navigator.permissions.query({name:'geolocation'}).then(status=>{if(off||status.state!=='granted')return;return geo().then(p=>{if(!off&&p)setPos(p)})}).catch(()=>undefined)
    return()=>{off=true}
  },[routeId,pos])

  useEffect(()=>{if(!routeId)return;let off=false;setError('');setLeg('')
    void Promise.all([getNeshanMapConfig(),getRouteMapPlan(routeId,mode==='sales'?'sales_priority':'shortest',trustedPos)])
      .then(([c,p])=>{if(!off){setKey(c.api_key ?? '');setPlan(p);const first=routeCluster(p)[0];if(first)primaryCustomerRef.current(String(first.id))}}).catch(e=>{if(!off)setError(e instanceof Error?e.message:'Neshan map unavailable')})
    return()=>{off=true}
  },[routeId,mode,trustedPos])

  useEffect(()=>{if(!key||!host.current||map.current)return;let dead=false,local:any=null,observer:ResizeObserver|null=null
    void Promise.all([loadSdk(),loadProxiedStyle(key)]).then(([sdk,proxiedStyle])=>{if(dead||!host.current||map.current)return
      const first=trustedCustomersRef.current[0],initialPos=trustedPosRef.current
      local=new sdk.Map({container:host.current,style:proxiedStyle,center:initialPos?[initialPos.longitude,initialPos.latitude]:first?[Number(first.longitude),Number(first.latitude)]:[51.4,35.7],zoom:initialPos?13:10,apiKey:key,rtl:{lazy:false}})
      sdkRef.current=sdk;map.current=local;local.addControl(new sdk.NavigationControl())
      observer=new ResizeObserver(()=>{if(!dead)window.requestAnimationFrame(()=>local?.resize?.())});observer.observe(host.current)
      local.on('error',(event:any)=>{if(dead)return;needsRecoveryRef.current=true;const message=String(event?.error?.message||'Neshan map rendering failed');console.warn('[Neshan map]',message)})
      local.on('load',()=>{if(dead)return;retryAttemptRef.current=0;needsRecoveryRef.current=false;setError('');setMapReady(true);window.requestAnimationFrame(()=>local?.resize?.())})
    }).catch(e=>{if(dead)return;map.current=null;sdkRef.current=null;setMapReady(false);setError(e instanceof Error?e.message:'Neshan SDK unavailable');retryAttemptRef.current+=1
      if(navigator.onLine){const delay=Math.min(15000,1000*(2**Math.min(retryAttemptRef.current,4)));if(retryTimerRef.current)window.clearTimeout(retryTimerRef.current);retryTimerRef.current=window.setTimeout(()=>setInitNonce(value=>value+1),delay)}
    })
    return()=>{dead=true;observer?.disconnect();if(retryTimerRef.current){window.clearTimeout(retryTimerRef.current);retryTimerRef.current=null}if(local&&map.current===local){local.remove();map.current=null;sdkRef.current=null;setMapReady(false)}}
  },[key,initNonce])

  useEffect(()=>{if(!mapReady||!map.current||!sdkRef.current)return;const current=map.current,sdk=sdkRef.current
    markers.current.forEach(marker=>marker.remove());markers.current=[]
    trustedCustomers.forEach((customer,index)=>{const el=document.createElement('button');el.type='button';el.className='vr-map-live-marker'+(String(customer.id)===selectedIdRef.current?' selected':'');el.textContent=String(index+1);el.setAttribute('aria-label',String(customer.name||('Customer '+(index+1))));el.setAttribute('aria-pressed',String(String(customer.id)===selectedIdRef.current));el.dataset.customerId=String(customer.id);el.onclick=()=>selectCustomerRef.current(String(customer.id));markers.current.push(new sdk.Marker({element:el}).setLngLat([Number(customer.longitude),Number(customer.latitude)]).addTo(current))})
    if(trustedPos){const el=document.createElement('span');el.className='vr-map-live-seller';markers.current.push(new sdk.Marker({element:el}).setLngLat([trustedPos.longitude,trustedPos.latitude]).addTo(current))}
  },[mapReady,trustedCustomers,trustedPos])

  useEffect(()=>{if(!host.current)return;host.current.querySelectorAll<HTMLElement>('.vr-map-live-marker').forEach(el=>{const selectedNow=el.dataset.customerId===selectedCustomerId;el.classList.toggle('selected',selectedNow);el.setAttribute('aria-pressed',String(selectedNow))})},[selectedCustomerId,mapReady,trustedCustomers])

  useEffect(()=>{if(!mapReady||!map.current)return;const first=trustedCustomers[0],focus=trustedCustomers.find(c=>String(c.id)===selectedCustomerId)??first;if(!focus)return
    const token=`${routeId??''}|${mode}|${selectedCustomerId}`;if(focusTokenRef.current===token)return;focusTokenRef.current=token
    if(trustedPos&&distanceKm(trustedPos,{latitude:Number(focus.latitude),longitude:Number(focus.longitude)})<=80){map.current.fitBounds([[trustedPos.longitude,trustedPos.latitude],[Number(focus.longitude),Number(focus.latitude)]],{padding:48,maxZoom:15.5,duration:0})}
    else{map.current.jumpTo({center:[Number(focus.longitude),Number(focus.latitude)],zoom:15})}
  },[mapReady,routeId,mode,selectedCustomerId,trustedCustomers,trustedPos])

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
  useEffect(()=>{if(!routeId||!trustedPos||!selected){setLeg('');return}let off=false;void getRouteMapLeg(routeId,String(selected.id),trustedPos).then(r=>{if(!off)setLeg(r.polyline||'')}).catch(e=>{if(!off)onNotice(e instanceof Error?e.message:'Live route unavailable')});return()=>{off=true}},[routeId,trustedPos,selected,onNotice])
  useEffect(()=>{if(!recenterNonce)return;let off=false;void geo().then(p=>{if(off)return;if(!p){onNotice('دسترسی GPS برقرار نیست یا موقعیت دریافت نشد.');return}setPos(p);if(!plan||gpsMatchesPlan(p,plan)){map.current?.flyTo({center:[p.longitude,p.latitude],zoom:15.5,duration:650,essential:true})}else{onNotice('موقعیت GPS با محدوده مسیر همخوان نیست و نادیده گرفته شد.')}});return()=>{off=true}},[recenterNonce,onNotice])

  return <div className="vr-map-live-shell"><div ref={host} className="vr-map-live" aria-label="نقشه زنده مسیر فروش"/>{!plan&&!error?<span className="vr-map-live-state">در حال بارگذاری نقشه…</span>:null}{error?<button type="button" className="vr-map-live-state error" onClick={()=>onNotice(error)}>نقشه در دسترس نیست</button>:null}</div>
}
