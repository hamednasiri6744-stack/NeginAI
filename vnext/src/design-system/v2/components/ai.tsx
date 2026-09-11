import {Bot,Camera,FileUp,Mic,Paperclip,Send,Square} from 'lucide-react'
import type {ReactNode} from 'react'
import {Button,IconButton} from './actions'
import {Badge} from './feedback'
export function PromptChips({items,onSelect}:{items:string[];onSelect?:(item:string)=>void}){return <div className="ng-prompt-chips">{items.map(i=><button type="button" key={i} onClick={()=>onSelect?.(i)}>{i}</button>)}</div>}
export function AIComposer({placeholder='ظ¾غŒط§ظ… ط®ظˆط¯ ط±ط§ ط¨ط±ط§غŒ ط¯ط³طھغŒط§ط± ط¨ظ†ظˆغŒط³غŒط¯â€¦',loading=false}:{placeholder?:string;loading?:boolean}){return <div className="ng-ai-composer"><textarea aria-label="ظ¾غŒط§ظ… ط¨ظ‡ ط¯ط³طھغŒط§ط± AI" placeholder={placeholder}/><div><span><IconButton label="ط§ظپط²ظˆط¯ظ† ظپط§غŒظ„"><Paperclip/></IconButton><IconButton label="ط¯ظˆط±ط¨غŒظ†"><Camera/></IconButton><IconButton label="ظ¾غŒط§ظ… طµظˆطھغŒ"><Mic/></IconButton></span><Button aria-label={loading?'طھظˆظ‚ظپ ظ¾ط§ط³ط®':'ط§ط±ط³ط§ظ„ ظ¾غŒط§ظ…'}>{loading?<Square size={16}/>:<Send size={17}/>}</Button></div></div>}
export function AIResponse({children,streaming=false}:{children:ReactNode;streaming?:boolean}){return <article className="ng-ai-response"><header><span><Bot/></span><strong>ط¯ط³طھغŒط§ط± Negin AI</strong>{streaming&&<Badge tone="info">ط¯ط± ط­ط§ظ„ ظ¾ط§ط³ط®</Badge>}</header><div>{children}{streaming&&<i className="ng-stream-caret"/>}</div><footer><button type="button">ظ…ظپغŒط¯ ط¨ظˆط¯</button><button type="button">ظ†غŒط§ط² ط¨ظ‡ ط§طµظ„ط§ط­</button></footer></article>}
export function ToolResultCard({title,status='ط¢ظ…ط§ط¯ظ‡ ط¨ط±ط±ط³غŒ',children}:{title:string;status?:string;children:ReactNode}){return <article className="ng-tool-result"><header><FileUp/><strong>{title}</strong><Badge tone="success">{status}</Badge></header><div>{children}</div><footer><Button variant="secondary" size="sm">ظ…ط´ط§ظ‡ط¯ظ‡ ط¬ط²ط¦غŒط§طھ</Button></footer></article>}
export function Attachment({name,type='ط³ظ†ط¯',size='â€”'}:{name:string;type?:string;size?:string}){return <div className="ng-attachment"><FileUp/><span><strong>{name}</strong><small>{type} آ· <span dir="ltr">{size}</span></small></span><IconButton label={`ط­ط°ظپ ${name}`}>أ—</IconButton></div>}
export function ContextualAIAction({label='ط§ط² ط¯ط³طھغŒط§ط± ط¨ظ¾ط±ط³غŒط¯'}:{label?:string}){return <Button variant="secondary" startIcon={<Bot/>}>{label}</Button>}

export function InsightCard({title,description,action='\u0645\u0634\u0627\u0647\u062f\u0647',tone='premium',icon=<Bot/>,onClick}:{title:string;description:string;action?:string;tone?:'neutral'|'premium'|'info'|'success'|'warning'|'danger'|'offline';icon?:ReactNode;onClick?:()=>void}){
  return <button type="button" className={`ng-insight-card ng-tone--${tone}`} onClick={onClick}><span className="ng-insight-card__icon">{icon}</span><span><strong>{title}</strong><small>{description}</small></span><b>{action}</b></button>
}

