import { MapPinned, Route, Users } from 'lucide-react'
import { navigate } from '../../app/router'
import { Alert, Button, Card, Cluster, EmptyState, PageHeader, ResponsivePageContainer, Spinner, Stack, StatusBadge } from '../../design-system/v2'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'

type SellerRoute={id:string;title?:string;customer_count?:number;row_index?:number;is_day_route?:boolean;can_start_day_route?:boolean}
type SellerRoutesResponse={visit_template?:string;day_route?:{id?:string;title?:string}|null;day_route_status?:string;routes?:SellerRoute[]}
const reviewData:SellerRoutesResponse={visit_template:'\u0648\u06cc\u0632\u06cc\u062a\u0648\u0631 \u06a9\u0631\u062c',day_route:{id:'R-01',title:'\u06a9\u0631\u062c \u0645\u0631\u06a9\u0632\u06cc'},day_route_status:'\u0622\u0645\u0627\u062f\u0647 \u0634\u0631\u0648\u0639',routes:[{id:'R-01',title:'\u06a9\u0631\u062c \u0645\u0631\u06a9\u0632\u06cc',customer_count:21,row_index:1,is_day_route:true,can_start_day_route:true},{id:'R-02',title:'\u06af\u0648\u0647\u0631\u062f\u0634\u062a',customer_count:18,row_index:2},{id:'R-03',title:'\u0645\u0647\u0631\u0634\u0647\u0631',customer_count:14,row_index:3}]}
const getRoutes=(signal:AbortSignal)=>apiRequest<SellerRoutesResponse>('/seller-workspace/routes',{signal})
const fa=(value:number)=>new Intl.NumberFormat('fa-IR').format(value)

export function SellerRoutesScreen(){
  const review=import.meta.env.DEV&&new URLSearchParams(window.location.search).get('review')==='1'
  const query=useApiQuery('seller:routes',(signal)=>review?Promise.resolve(reviewData):getRoutes(signal))
  const data=query.data
  const routes=data?.routes??[]
  return <div className="ng-v2" dir="rtl" data-trace-id="SEL-01"><ResponsivePageContainer><Stack gap={5}>
    <PageHeader eyebrow="SELLER / ROUTES" title={'\u0645\u0633\u06cc\u0631\u0647\u0627\u06cc \u0645\u0646'} description={'\u0645\u0633\u06cc\u0631 \u0627\u0645\u0631\u0648\u0632 \u0631\u0627 \u0627\u0646\u062a\u062e\u0627\u0628 \u06a9\u0646\u06cc\u062f \u0648 \u0648\u06cc\u0632\u06cc\u062a \u0631\u0627 \u0628\u0627 \u0627\u0648\u0644\u0648\u06cc\u062a \u0641\u0631\u0648\u0634 \u0627\u062f\u0627\u0645\u0647 \u062f\u0647\u06cc\u062f.'}/>
    {query.status==='loading'&&!data?<Card><Cluster><Spinner/><strong>{'\u062f\u0631 \u062d\u0627\u0644 \u062f\u0631\u06cc\u0627\u0641\u062a \u0645\u0633\u06cc\u0631\u0647\u0627...'}</strong></Cluster></Card>:null}
    {query.status==='error'?<Alert title={'\u062f\u0631\u06cc\u0627\u0641\u062a \u0645\u0633\u06cc\u0631\u0647\u0627 \u0646\u0627\u0645\u0648\u0641\u0642 \u0628\u0648\u062f'} tone="danger">{query.error?.message}</Alert>:null}
    {query.status==='success'&&routes.length===0?<EmptyState title={'\u0645\u0633\u06cc\u0631\u06cc \u062a\u062e\u0635\u06cc\u0635 \u062f\u0627\u062f\u0647 \u0646\u0634\u062f\u0647'} description={'\u0628\u0631\u0627\u06cc \u0627\u06cc\u0646 \u062d\u0633\u0627\u0628 \u0645\u0633\u06cc\u0631 \u0641\u0639\u0627\u0644\u06cc \u0648\u062c\u0648\u062f \u0646\u062f\u0627\u0631\u062f.'}/>:null}
    {data&&routes.length?<><div className="ng-stat-strip"><div><span>{'\u067e\u0631\u0648\u0641\u0627\u06cc\u0644 \u0641\u0631\u0648\u0634'}</span><strong>{data.visit_template||'\u2014'}</strong></div><div><span>{'\u0645\u0633\u06cc\u0631 \u0627\u0645\u0631\u0648\u0632'}</span><strong>{data.day_route?.title||'\u2014'}</strong></div><div><span>{'\u0648\u0636\u0639\u06cc\u062a'}</span><strong>{data.day_route_status||'\u2014'}</strong></div></div><Stack gap={3}>{routes.map(item=><Card key={item.id} interactive className="ng-route-v2"><Cluster><span className="ng-route-v2__icon"><Route/></span><div className="ng-route-v2__copy"><strong>{item.title||item.id}</strong><small>{typeof item.customer_count==='number'?`${fa(item.customer_count)} \u0645\u0634\u062a\u0631\u06cc`:item.id}</small></div>{item.is_day_route?<StatusBadge label={'\u0645\u0633\u06cc\u0631 \u0627\u0645\u0631\u0648\u0632'} tone="premium"/>:null}</Cluster><Cluster><span><Users size={16}/> {fa(item.customer_count??0)} {'\u0645\u0634\u062a\u0631\u06cc'}</span><Button variant="secondary" startIcon={<MapPinned/>} onClick={()=>navigate('/seller/customers')}>{'\u0645\u0634\u062a\u0631\u06cc\u200c\u0647\u0627'}</Button><Button onClick={()=>navigate('/seller/day-route')}>{'\u0628\u0627\u0632 \u06a9\u0631\u062f\u0646 \u0645\u0633\u06cc\u0631'}</Button></Cluster></Card>)}</Stack></>:null}
  </Stack></ResponsivePageContainer></div>
}
