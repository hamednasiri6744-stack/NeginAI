import type { CSSProperties, HTMLAttributes, ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import {cx} from '../utilities'

export function Text({as:Tag='p',variant='body',className,...props}:HTMLAttributes<HTMLElement>&{as?:'p'|'span'|'strong'|'small'|'h1'|'h2'|'h3';variant?:'display'|'page'|'section'|'card'|'body'|'secondary'|'caption'|'label'|'numeric'}){
  return <Tag className={cx('ng-text',`ng-text--${variant}`,className)} {...props}/>
}
export function Icon({icon:Glyph,label,size=20,className}:{icon:LucideIcon;label?:string;size?:number;className?:string}){return <Glyph className={className} size={size} aria-hidden={label?undefined:true} aria-label={label} role={label?'img':undefined}/>} 
export function Divider({label}: {label?:string}){return <div className="ng-divider" role="separator">{label&&<span>{label}</span>}</div>}
export function Surface({level=1,glass=false,className,...props}:HTMLAttributes<HTMLDivElement>&{level?:1|2|3|4;glass?:boolean}){return <div className={cx('ng-surface',`ng-surface--${level}`,glass&&'ng-surface--glass',className)} {...props}/>} 
export function Stack({gap=4,className,style,...props}:HTMLAttributes<HTMLDivElement>&{gap?:1|2|3|4|5|6|8|10|12}){return <div className={cx('ng-stack',className)} style={{'--ng-stack-gap':`var(--ng-space-${gap})`,...style} as CSSProperties} {...props}/>} 
export function Cluster({gap=3,className,style,...props}:HTMLAttributes<HTMLDivElement>&{gap?:1|2|3|4|5|6|8}){return <div className={cx('ng-cluster',className)} style={{'--ng-cluster-gap':`var(--ng-space-${gap})`,...style} as CSSProperties} {...props}/>} 
export function Container({wide=false,className,...props}:HTMLAttributes<HTMLDivElement>&{wide?:boolean}){return <div className={cx('ng-container',wide&&'ng-container--wide',className)} {...props}/>} 
export function ScrollArea({label='ناحیه پیمایش',className,...props}:HTMLAttributes<HTMLDivElement>&{label?:string}){return <div className={cx('ng-scroll-area',className)} role="region" aria-label={label} tabIndex={0} {...props}/>} 
export function VisuallyHidden({children}:{children:ReactNode}){return <span className="ng-sr-only">{children}</span>}
