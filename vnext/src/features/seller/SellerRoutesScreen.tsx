import { MapPinned, Route, Users } from 'lucide-react'
import { navigate } from '../../app/router'
import { Button, Card, Cluster, PageHeader, ResponsivePageContainer, Stack, StatusBadge } from '../../design-system/v2'
import { AsyncState } from '../../components/AsyncState'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'

type SellerRoute={id:string;title?:string;customer_count?:number;row_index?:number;is_day_route?:boolean;can_start_day_route?:boolean}
type SellerRoutesResponse={visit_template?:string;day_route?:{id?:string;title?:string}|null;day_route_status?:string;routes?:SellerRoute[]}
const reviewData:SellerRoutesResponse={visit_template:'ویزیتور کرج',day_route:{id:'R-01',title:'کرج مرکزی'},day_route_status:'آماده شروع',routes:[{id:'R-01',title:'کرج مرکزی',customer_count:21,row_index:1,is_day_route:true,can_start_day_route:true},{id:'R-02',title:'گوهردشت',customer_count:18,row_index:2},{id:'R-03',title:'مهرشهر',customer_count:14,row_index:3}]}
const getRoutes=(signal:AbortSignal)=>apiRequest<SellerRoutesResponse>('/seller-workspace/routes',{signal})
const fa=(value:number)=>new Intl.NumberFormat('fa-IR').format(value)

export function SellerRoutesScreen(){
  const review=import.meta.env.DEV&&new URLSearchParams(window.location.search).get('review')==='1'
  const query=useApiQuery('seller:routes',(signal)=>review?Promise.resolve(reviewData):getRoutes(signal))
  const data=query.data
  return <div className="ng-v2" dir="rtl" data-trace-id="SEL-01"><ResponsivePageContainer><Stack gap={5}>
    <PageHeader eyebrow="SELLER / ROUTES" title="مسیرهای من" description="مسیر امروز را انتخاب کنید و ویزیت را با اولویت فروش ادامه دهید."/>
    {query.status==='loading'&&!data?<AsyncState mode="loading" title="در حال دریافت مسیرها"/>:null}
    {query.status==='error'?<AsyncState mode="error" title="دریافت مسیرها ناموفق بود" message={query.error?.message} onRetry={query.reload}/>:null}
    {data?<><div className="ng-stat-strip"><div><span>پروفایل فروش</span><strong>{data.visit_template||'—'}</strong></div><div><span>مسیر امروز</span><strong>{data.day_route?.title||'—'}</strong></div><div><span>وضعیت</span><strong>{data.day_route_status||'—'}</strong></div></div><Stack gap={3}>{(data.routes??[]).map(item=><Card key={item.id} interactive className="ng-route-card"><Cluster><span className="ng-route-card-icon"><Route/></span><div className="ng-route-card-copy"><strong>{item.title||item.id}</strong><small>{typeof item.customer_count==='number'?`${fa(item.customer_count)} مشتری`:item.id}</small></div>{item.is_day_route?<StatusBadge label="مسیر امروز" tone="premium"/>:null}</Cluster><Cluster><span><Users size={16}/> {fa(item.customer_count??0)} مشتری</span><Button variant="secondary" startIcon={<MapPinned/>} onClick={()=>navigate('/seller/customers')}>مشتری‌ها</Button><Button onClick={()=>navigate('/seller/day-route')}>باز کردن مسیر</Button></Cluster></Card>)}</Stack></>:null}
  </Stack></ResponsivePageContainer></div>
}
