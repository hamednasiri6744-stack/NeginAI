import {AlertCircle,CheckCircle2,CloudOff,Info,LoaderCircle,LockKeyhole,TriangleAlert,XCircle} from 'lucide-react'
import type {ReactNode} from 'react'
import {Button} from './actions'
import {cx} from '../utilities'
export type Tone='neutral'|'premium'|'info'|'success'|'warning'|'danger'|'offline'
const icons={neutral:Info,premium:Info,info:Info,success:CheckCircle2,warning:TriangleAlert,danger:XCircle,offline:CloudOff}
export function Badge({children,tone='neutral'}:{children:ReactNode;tone?:Tone}){return <span className={cx('ng-badge',`ng-tone--${tone}`)}>{children}</span>}
export function StatusBadge({label,tone='neutral'}:{label:string;tone?:Tone}){const Glyph=icons[tone];return <span className={cx('ng-status',`ng-tone--${tone}`)}><Glyph size={14}/>{label}</span>}
export function Alert({title,children,tone='info',action}:{title:string;children?:ReactNode;tone?:Tone;action?:ReactNode}){const Glyph=icons[tone];return <div className={cx('ng-alert',`ng-tone--${tone}`)} role={tone==='danger'?'alert':'status'}><Glyph size={20}/><div><strong>{title}</strong>{children&&<p>{children}</p>}</div>{action}</div>}
export function Progress({value,label}:{value:number;label:string}){const v=Math.max(0,Math.min(100,value));return <div className="ng-progress"><div><span>{label}</span><span dir="ltr">{v}%</span></div><div role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={v}><span style={{inlineSize:`${v}%`}}/></div></div>}
export function Spinner({label='در حال بارگذاری'}:{label?:string}){return <span className="ng-spinner" role="status"><LoaderCircle className="ng-spin"/><span className="ng-sr-only">{label}</span></span>}
export function Skeleton({lines=3}:{lines?:number}){return <div className="ng-skeleton" role="status" aria-label="در حال بارگذاری محتوا">{Array.from({length:lines},(_,i)=><span key={i}/>)}</div>}
type StateProps={title:string;description:string;actionLabel?:string;onAction?:()=>void}
function State({icon,title,description,actionLabel,onAction,tone='neutral'}:StateProps&{icon:ReactNode;tone?:Tone}){return <div className={cx('ng-state',`ng-tone--${tone}`)}>{icon}<strong>{title}</strong><p>{description}</p>{actionLabel&&<Button variant="secondary" onClick={onAction}>{actionLabel}</Button>}</div>}
export function EmptyState(props:Partial<StateProps>){return <State icon={<Info/>} title={props.title??'هنوز موردی ثبت نشده'} description={props.description??'پس از ایجاد، اطلاعات اینجا نمایش داده می‌شود.'} actionLabel={props.actionLabel} onAction={props.onAction}/>} 
export function ErrorState(props:Partial<StateProps>){return <State icon={<AlertCircle/>} tone="danger" title={props.title??'بازیابی اطلاعات ممکن نشد'} description={props.description??'دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.'} actionLabel={props.actionLabel??'تلاش دوباره'} onAction={props.onAction}/>} 
export function OfflineState(props:Partial<StateProps>){return <State icon={<CloudOff/>} tone="offline" title={props.title??'اتصال شبکه برقرار نیست'} description={props.description??'داده‌های در دسترس دستگاه همچنان قابل مشاهده‌اند.'} actionLabel={props.actionLabel} onAction={props.onAction}/>} 
export function PermissionDeniedState(props:Partial<StateProps>){return <State icon={<LockKeyhole/>} tone="warning" title={props.title??'دسترسی مجاز نیست'} description={props.description??'سطح دسترسی این بخش برای نقش فعلی فعال نشده است.'}/>} 
export function Toast({message,tone='neutral',action}:{message:string;tone?:Tone;action?:ReactNode}){return <div className={cx('ng-toast',`ng-tone--${tone}`)} role={tone==='danger'?'alert':'status'}><StatusBadge label={message} tone={tone}/>{action}</div>}
