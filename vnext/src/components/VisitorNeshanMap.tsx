import { useEffect, useMemo, useRef, useState } from 'react'
import { getNeshanMapConfig, getRouteMapLeg, getRouteMapPlan, type NeshanRouteMapPlanResponse } from '../api/neginApi'

type Props={routeId:string|null;mode:'sales'|'shortest';selectedCustomerId:string;recenterNonce:number;onSelectCustomer:(id:string)=>void;onNotice:(m:string)=>void}
type Pos={latitude:number;longitude:number}
type ML={Map:new(o:Record<string,unknown>)=>any;Marker:new(o?:Record<string,unknown>)=>any;NavigationControl:new()=>unknown}
const CSS='https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.css'
const JS='https://static.neshan.org/sdk/maplibre/5.24.3/neshan-maplibre-sdk.umd.js'
const STYLE='https://static.neshan.org/sdk/maplibre/styles/light.json'

function fromWindow(){const v=(window as unknown as{maplibregl?:ML&{default?:ML}}).maplibregl;return v?.default??v??null}
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
function draw(map:any,encoded:string){
  if(!map?.isStyleLoaded())return
  if(map.getLayer('v017-route'))map.removeLayer('v017-route')
  if(map.getSource('v017-route'))map.removeSource('v017-route')
  const c=decode(encoded);if(c.length<2)return
  map.addSource('v017-route',{type:'geojson',data:{type:'Feature',properties:{},geometry:{type:'LineString',coordinates:c}}})
  map.addLayer({id:'v017-route',type:'line',source:'v017-route',paint:{'line-color':'#e8b64f','line-width':5,'line-opacity':.9}})
}

export function VisitorNeshanMap({routeId,mode,selectedCustomerId,recenterNonce,onSelectCustomer,onNotice}:Props){
  const host=useRef<HTMLDivElement|null>(null),map=useRef<any>(null),markers=useRef<any[]>([])
  const [plan,setPlan]=useState<NeshanRouteMapPlanResponse|null>(null),[key,setKey]=useState(''),[pos,setPos]=useState<Pos|null>(null),[leg,setLeg]=useState(''),[error,setError]=useState('')
  const poly=leg||plan?.polyline||''
  const selected=useMemo(()=>plan?.ordered_customers.find(c=>String(c.id)===selectedCustomerId)??null,[plan,selectedCustomerId])

  useEffect(()=>{if(!routeId)return;let off=false;setError('');setLeg('')
    void Promise.all([getNeshanMapConfig(),getRouteMapPlan(routeId,mode==='sales'?'sales_priority':'shortest',null)])
      .then(([c,p])=>{if(!off){setKey(c.api_key ?? '');setPlan(p)}}).catch(e=>{if(!off)setError(e instanceof Error?e.message:'Neshan map unavailable')})
    return()=>{off=true}
  },[routeId,mode])

  useEffect(()=>{if(!plan||!key||!host.current)return;let dead=false,local:any=null
    void loadSdk().then(sdk=>{if(dead||!host.current)return
      const first=plan.ordered_customers.find(c=>c.latitude!=null&&c.longitude!=null)
      local=new sdk.Map({container:host.current,style:STYLE,center:pos?[pos.longitude,pos.latitude]:first?[Number(first.longitude),Number(first.latitude)]:[51.4,35.7],zoom:pos?13:10,apiKey:key,rtl:{lazy:false}})
      map.current=local;local.addControl(new sdk.NavigationControl())
      local.on('load',()=>{if(dead)return;markers.current.forEach(m=>m.remove());markers.current=[]
        const pts:Array<[number,number]>=[]
        plan.ordered_customers.forEach((c,n)=>{if(c.latitude==null||c.longitude==null)return;const el=document.createElement('button');el.type='button';el.className='vr-map-live-marker'+(String(c.id)===selectedCustomerId?' selected':'');el.textContent=String(n+1);el.setAttribute('aria-label',String(c.name||('Customer '+(n+1))));el.setAttribute('aria-pressed',String(String(c.id)===selectedCustomerId));el.onclick=()=>onSelectCustomer(String(c.id));const xy:[number,number]=[Number(c.longitude),Number(c.latitude)];markers.current.push(new sdk.Marker({element:el}).setLngLat(xy).addTo(local));pts.push(xy)})
        if(pos){const el=document.createElement('span');el.className='vr-map-live-seller';markers.current.push(new sdk.Marker({element:el}).setLngLat([pos.longitude,pos.latitude]).addTo(local));pts.push([pos.longitude,pos.latitude])}
        if(pts.length>1){const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);local.fitBounds([[Math.min(...xs),Math.min(...ys)],[Math.max(...xs),Math.max(...ys)]],{padding:42,maxZoom:14,duration:0})}
        draw(local,poly)
      })
    }).catch(e=>setError(e instanceof Error?e.message:'Neshan SDK unavailable'))
    return()=>{dead=true;markers.current.forEach(m=>m.remove());markers.current=[];local?.remove();if(map.current===local)map.current=null}
  },[key,plan,pos,selectedCustomerId,onSelectCustomer])

  useEffect(()=>{draw(map.current,poly)},[poly])
  useEffect(()=>{if(!routeId||!pos||!selected){setLeg('');return}let off=false;void getRouteMapLeg(routeId,String(selected.id),pos).then(r=>{if(!off)setLeg(r.polyline||'')}).catch(e=>{if(!off)onNotice(e instanceof Error?e.message:'Live route unavailable')});return()=>{off=true}},[routeId,pos,selected,onNotice])
  useEffect(()=>{if(!recenterNonce)return;let off=false;void geo().then(p=>{if(off)return;if(!p){onNotice('دسترسی GPS برقرار نیست یا موقعیت دریافت نشد.');return}setPos(p);map.current?.flyTo({center:[p.longitude,p.latitude],zoom:15.5,duration:650,essential:true})});return()=>{off=true}},[recenterNonce,onNotice])

  return <div className="vr-map-live-shell"><div ref={host} className="vr-map-live" aria-label="نقشه زنده مسیر فروش"/>{!plan&&!error?<span className="vr-map-live-state">در حال بارگذاری نقشه…</span>:null}{error?<button type="button" className="vr-map-live-state error" onClick={()=>onNotice(error)}>نقشه در دسترس نیست</button>:null}</div>
}
