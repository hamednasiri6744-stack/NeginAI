import {ChevronLeft,Clock3} from 'lucide-react'
import type {HTMLAttributes,ReactNode} from 'react'
import {cx} from '../utilities'
import {Badge,StatusBadge,type Tone} from './feedback'
export function Card({interactive=false,className,...props}:HTMLAttributes<HTMLElement>&{interactive?:boolean}){return <article className={cx('ng-card',interactive&&'is-interactive',className)} {...props}/>} 
export function MetricCard({label,value,detail,trend,tone='neutral'}:{label:string;value:ReactNode;detail?:string;trend?:string;tone?:Tone}){return <Card className="ng-metric"><span>{label}</span><strong dir="auto">{value}</strong><div>{detail&&<small>{detail}</small>}{trend&&<Badge tone={tone}>{trend}</Badge>}</div></Card>}
export const KPITile=MetricCard
export function StatStrip({items}:{items:Array<{label:string;value:string}>}){return <div className="ng-stat-strip">{items.map(i=><div key={i.label}><span>{i.label}</span><strong>{i.value}</strong></div>)}</div>}
export function ListItem({title,description,meta,leading,trailing,onClick}:{title:string;description?:string;meta?:string;leading?:ReactNode;trailing?:ReactNode;onClick?:()=>void}){const Tag=onClick?'button':'div';return <Tag className="ng-list-item" onClick={onClick}>{leading}<span><strong>{title}</strong>{description&&<small>{description}</small>}</span>{meta&&<small>{meta}</small>}{trailing??(onClick&&<ChevronLeft size={18}/>)}</Tag>}
export const DataRow=ListItem
export function KeyValue({items}:{items:Array<{key:string;value:ReactNode}>}){return <dl className="ng-key-value">{items.map(i=><div key={i.key}><dt>{i.key}</dt><dd>{i.value}</dd></div>)}</dl>}
export function Timeline({items}:{items:Array<{title:string;detail:string;time:string;tone?:Tone}>}){return <ol className="ng-timeline">{items.map((i,n)=><li key={`${i.title}-${n}`}><span/><div><strong>{i.title}</strong><p>{i.detail}</p><small><Clock3 size={14}/>{i.time}</small></div></li>)}</ol>}
export const ActivityItem=ListItem
export type Column<T>={key:keyof T;label:string;numeric?:boolean;render?:(value:T[keyof T],row:T)=>ReactNode}
export function Table<T extends Record<string,unknown>>({caption,columns,rows,dense=false}:{caption:string;columns:Array<Column<T>>;rows:T[];dense?:boolean}){return <div className={cx('ng-table-wrap',dense&&'is-dense')} role="region" aria-label={caption} tabIndex={0}><table><caption>{caption}</caption><thead><tr>{columns.map(c=><th key={String(c.key)} scope="col" className={c.numeric?'is-numeric':undefined}>{c.label}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{columns.map(c=><td key={String(c.key)} data-label={c.label} className={c.numeric?'is-numeric':undefined}>{c.render?c.render(row[c.key],row):String(row[c.key]??'—')}</td>)}</tr>)}</tbody></table></div>}
export function DataStatus({label,tone}:{label:string;tone:Tone}){return <StatusBadge label={label} tone={tone}/>}

export function Sparkline({values=[4,7,6,9,8,11],tone='success',label='\u0631\u0648\u0646\u062f'}:{values?:number[];tone?:Tone;label?:string}){
  const series=values.length?values:[0],min=Math.min(...series),max=Math.max(...series),range=Math.max(1,max-min),denom=Math.max(1,series.length-1)
  const points=series.map((value,index)=>`${((index/denom)*100).toFixed(2)},${(28-((value-min)/range)*24).toFixed(2)}`).join(' ')
  const last=points.split(' ').at(-1)?.split(',')
  return <svg className={cx('ng-sparkline',`ng-tone--${tone}`)} viewBox="0 0 100 32" role="img" aria-label={label} preserveAspectRatio="none"><polyline points={points} fill="none" vectorEffect="non-scaling-stroke"/>{last&&<circle cx={last[0]} cy={last[1]} r="2.2"/>}</svg>
}
export function ProgressRing({value,label='\u067e\u06cc\u0634\u0631\u0641\u062a',detail,tone='premium'}:{value:number;label?:string;detail?:string;tone?:Tone}){
  const safe=Math.max(0,Math.min(100,value)),radius=23,c=2*Math.PI*radius,offset=c*(1-safe/100)
  return <div className={cx('ng-progress-ring',`ng-tone--${tone}`)}><svg viewBox="0 0 56 56" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(safe)}><circle className="ng-progress-ring__track" cx="28" cy="28" r={radius}/><circle className="ng-progress-ring__value" cx="28" cy="28" r={radius} strokeDasharray={c} strokeDashoffset={offset}/></svg><div><strong>{Math.round(safe).toLocaleString('fa-IR')}%</strong><span>{label}</span>{detail&&<small>{detail}</small>}</div></div>
}
export function VisualMetricCard({label,value,detail,trend,tone='success',values}:{label:string;value:ReactNode;detail?:string;trend?:string;tone?:Tone;values?:number[]}){
  return <Card className="ng-metric ng-metric--visual"><span>{label}</span><strong dir="auto">{value}</strong><div className="ng-metric__visual"><Sparkline values={values} tone={tone} label={label}/></div><div>{detail&&<small>{detail}</small>}{trend&&<Badge tone={tone}>{trend}</Badge>}</div></Card>
}
