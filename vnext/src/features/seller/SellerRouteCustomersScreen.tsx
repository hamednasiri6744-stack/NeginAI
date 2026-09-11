import { MapPin, Phone, Store } from 'lucide-react'
import { navigate } from '../../app/router'
import { Button, Card, Cluster, PageHeader, ResponsivePageContainer, SearchInput, Stack, StatusBadge } from '../../design-system/v2'
import { AsyncState } from '../../components/AsyncState'
import { apiRequest } from '../../lib/api/client'
import { useApiQuery } from '../../lib/api/useApiQuery'

type Customer={id:string|number;code?:string;name?:string;store_name?:string;address?:string;phone?:string;mobile?:string;latitude?:number|null;longitude?:number|null;open_invoice_count?:number}
type Response={route?:{id?:string;title?:string};customers?:Customer[];customer_count?:number}
const reviewData:Response={route:{id:'R-01',title:'کرج مرکزی'},customer_count:3,customers:[
{id:1,code:'C-1021',store_name:'فروشگاه بهار',name:'علی رضایی',mobile:'0912•••1842',address:'گوهردشت، بلوار اصلی',latitude:35.83,longitude:50.97,open_invoice_count:2},
{id:2,code:'C-1088',store_name:'سوپرمارکت نارون',name:'محمد حسینی',mobile:'0912•••5120',address:'رجایی‌شهر',latitude:35.80,longitude:50.99,open_invoice_count:0},
{id:3,code:'C-1114',store_name:'هایپر آریا',name:'امیر کریمی',mobile:'0935•••2401',address:'کرج، میدان اصلی',latitude:35.82,longitude:50.95,open_invoice_count:1}
]}

export function SellerRouteCustomersScreen(){
  const review=import.meta.env.DEV&&new URLSearchParams(window.location.search).get('review')==='1'
  const pathId=new URLSearchParams(window.location.search).get('pathId')?.trim()??''
  const query=useApiQuery<Response>(`seller:customers:${pathId||(review?'review':'missing')}`,(signal)=>review?Promise.resolve(reviewData):pathId?apiRequest<Response>(`/seller-workspace/routes/${encodeURIComponent(pathId)}/customers`,{signal}):Promise.reject(new Error('Missing route id')))
  const customers=query.data?.customers??[]
  return <div className="ng-v2" dir="rtl" data-trace-id="SEL-03"><ResponsivePageContainer><Stack gap={5}>
    <PageHeader eyebrow="ROUTE / CUSTOMERS" title={query.data?.route?.title||'مشتری‌های مسیر'} description="مشتری بعدی را براساس اولویت، موقعیت و وضعیت مالی انتخاب کنید." actions={<Button variant="secondary" onClick={()=>navigate('/seller/map')}>نمایش نقشه</Button>}/>
    <SearchInput label="جستجوی مشتری" placeholder="نام فروشگاه، مشتری یا کد"/>
    {query.status==='loading'&&!query.data?<AsyncState mode="loading" title="در حال دریافت مشتری‌ها"/>:null}
    {query.status==='error'?<AsyncState mode="error" title="دریافت مشتری‌ها ناموفق بود" message={query.error?.message} onRetry={query.reload}/>:null}
    {query.status==='success'&&customers.length===0?<AsyncState mode="empty" title="مشتری‌ای در این مسیر نیست"/>:null}
    {query.data?<Stack gap={3}><StatusBadge label={`${new Intl.NumberFormat('fa-IR').format(query.data.customer_count??customers.length)} مشتری`} tone="premium"/>{customers.map((c,index)=><Card key={String(c.id)} interactive><Cluster><span className="ng-product-thumb"><Store/></span><div style={{flex:1}}><strong>{c.store_name||c.name||String(c.id)}</strong><small>{[c.code&&`#${c.code}`,c.name].filter(Boolean).join(' · ')}</small></div><StatusBadge label={index===0?'اولویت بالا':c.open_invoice_count?'دارای مانده':'فعال'} tone={index===0?'premium':c.open_invoice_count?'warning':'success'}/></Cluster><Cluster>{c.address?<span><MapPin size={15}/> {c.address}</span>:null}{c.mobile||c.phone?<span><Phone size={15}/> {c.mobile||c.phone}</span>:null}<Button onClick={()=>navigate('/seller/customer')}>Customer 360</Button></Cluster></Card>)}</Stack>:null}
  </Stack></ResponsivePageContainer></div>
}
