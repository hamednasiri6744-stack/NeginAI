import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { CheckCircle2, Download, LockKeyhole, LogIn, UserRound, WifiOff } from 'lucide-react'
import { Alert, Button, PasswordInput, Spinner, Stack, StatusBadge, Surface, Text, TextInput } from '../../design-system/v2'
import { apiRequest, ApiError } from '../../lib/api/client'
import { clearApiQueryCache } from '../../lib/api/useApiQuery'
import { AuthContext, type AuthProfile } from './auth-context'

export function AuthGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<'checking'|'anonymous'|'success'|'authenticated'>('checking')
  const [profile, setProfile] = useState<AuthProfile|null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [isOnline, setIsOnline] = useState(()=>typeof navigator==='undefined'||navigator.onLine)
  const showAndroidDownload = typeof navigator!=='undefined' && /Android/i.test(navigator.userAgent) && !/NeginSellerAndroid\//i.test(navigator.userAgent)

  useEffect(()=>{
    const sync=()=>setIsOnline(navigator.onLine)
    window.addEventListener('online',sync); window.addEventListener('offline',sync)
    return()=>{window.removeEventListener('online',sync);window.removeEventListener('offline',sync)}
  },[])

  useEffect(()=>{
    const controller=new AbortController()
    apiRequest<AuthProfile>('/auth/me',{signal:controller.signal})
      .then(value=>{if(controller.signal.aborted)return;setProfile(value);setState('authenticated')})
      .catch((reason:unknown)=>{
        if(controller.signal.aborted)return
        if(!(reason instanceof ApiError&&reason.status===401))console.error('NeginAI session check failed',reason)
        setState('anonymous')
      })
    return()=>controller.abort()
  },[])

  async function login(event:FormEvent<HTMLFormElement>){
    event.preventDefault()
    const cleanUsername=username.trim()
    if(!isOnline){setError('\u0627\u062a\u0635\u0627\u0644 \u0634\u0628\u06a9\u0647 \u0628\u0631\u0642\u0631\u0627\u0631 \u0646\u06cc\u0633\u062a.');return}
    if(!cleanUsername||!password){setError('\u0646\u0627\u0645 \u06a9\u0627\u0631\u0628\u0631\u06cc \u0648 \u0631\u0645\u0632 \u0639\u0628\u0648\u0631 \u0631\u0627 \u0648\u0627\u0631\u062f \u06a9\u0646\u06cc\u062f.');return}
    setPending(true);setError('')
    try{
      const value=await apiRequest<AuthProfile>('/auth/login',{method:'POST',body:{username:cleanUsername,password}})
      clearApiQueryCache();setProfile(value);setState('success');window.setTimeout(()=>setState('authenticated'),360)
    }catch(reason){
      setError(reason instanceof ApiError&&reason.status===401
        ?'\u0646\u0627\u0645 \u06a9\u0627\u0631\u0628\u0631\u06cc \u06cc\u0627 \u0631\u0645\u0632 \u0639\u0628\u0648\u0631 \u0627\u0634\u062a\u0628\u0627\u0647 \u0627\u0633\u062a.'
        :reason instanceof ApiError&&(reason.kind==='network'||reason.kind==='timeout')
          ?'\u0627\u0631\u062a\u0628\u0627\u0637 \u0628\u0627 \u0633\u0631\u0648\u0631 \u0628\u0631\u0642\u0631\u0627\u0631 \u0646\u0634\u062f.'
          :reason instanceof Error?reason.message:'\u062e\u0637\u0627 \u062f\u0631 \u0648\u0631\u0648\u062f.')
    }finally{setPending(false)}
  }

  async function logout(){
    try{await apiRequest('/auth/logout',{method:'POST'})}
    finally{clearApiQueryCache();setProfile(null);setPassword('');setState('anonymous')}
  }

  const context=useMemo(()=>({profile,logout}),[profile])

  if(state==='checking')return <main className="ng-v2 ng-auth-v2" dir="rtl"><Surface glass className="ng-auth-v2__status"><Stack gap={4}><Spinner label={'\u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc \u0646\u0634\u0633\u062a'}/><Text as="strong" variant="card">{'\u062f\u0631 \u062d\u0627\u0644 \u0628\u0631\u0631\u0633\u06cc \u0646\u0634\u0633\u062a...'}</Text></Stack></Surface></main>

  if(state==='success')return <main className="ng-v2 ng-auth-v2" dir="rtl"><Surface glass className="ng-auth-v2__status"><Stack gap={4}><CheckCircle2 size={36}/><StatusBadge label={'\u0648\u0631\u0648\u062f \u0645\u0648\u0641\u0642'} tone="success"/><Text variant="secondary">{'\u062f\u0631 \u062d\u0627\u0644 \u0648\u0631\u0648\u062f \u0628\u0647 Negin AI...'}</Text></Stack></Surface></main>

  if(state==='anonymous')return (
    <main className="ng-v2 ng-auth-v2" dir="rtl" data-trace-id="AUTH-01">
      <Surface glass className="ng-auth-v2__card">
        <div className="ng-auth-v2__identity">
          <span className="ng-auth-v2__mark" aria-hidden="true">N</span>
          <StatusBadge label="Design System v2" tone="premium"/>
          <Text as="h1" variant="display">Negin AI</Text>
          <Text variant="secondary">{'\u067e\u0644\u062a\u0641\u0631\u0645 \u0639\u0645\u0644\u06cc\u0627\u062a\u06cc \u0648 \u0647\u0648\u0634\u0645\u0646\u062f \u0646\u06af\u06cc\u0646 \u067e\u062e\u0634'}</Text>
        </div>
        <form className="ng-auth-v2__form" onSubmit={login} aria-busy={pending}>
          <Stack gap={5}>
            <div>
              <Text as="h2" variant="page">{'\u0648\u0631\u0648\u062f \u0628\u0647 \u0633\u0627\u0645\u0627\u0646\u0647'}</Text>
              <Text variant="secondary">{'\u0628\u0631\u0627\u06cc \u0627\u062f\u0627\u0645\u0647 \u0627\u0637\u0644\u0627\u0639\u0627\u062a \u062d\u0633\u0627\u0628 \u062e\u0648\u062f \u0631\u0627 \u0648\u0627\u0631\u062f \u06a9\u0646\u06cc\u062f.'}</Text>
            </div>
            {!isOnline?<Alert title={'\u0622\u0641\u0644\u0627\u06cc\u0646'} tone="offline"><WifiOff size={16}/>{' \u0627\u062a\u0635\u0627\u0644 \u0634\u0628\u06a9\u0647 \u0628\u0631\u0642\u0631\u0627\u0631 \u0646\u06cc\u0633\u062a.'}</Alert>:null}
            {error?<Alert title={'\u0648\u0631\u0648\u062f \u0646\u0627\u0645\u0648\u0641\u0642'} tone="danger">{error}</Alert>:null}
            <TextInput id="username" label={'\u0646\u0627\u0645 \u06a9\u0627\u0631\u0628\u0631\u06cc'} leading={<UserRound size={18}/>} value={username} onChange={e=>{setUsername(e.target.value);if(error)setError('')}} autoComplete="username" disabled={pending} required/>
            <PasswordInput id="password" label={'\u0631\u0645\u0632 \u0639\u0628\u0648\u0631'} leading={<LockKeyhole size={18}/>} value={password} onChange={e=>{setPassword(e.target.value);if(error)setError('')}} autoComplete="current-password" disabled={pending} required/>
            <Button type="submit" size="lg" loading={pending} disabled={!isOnline} startIcon={<LogIn size={18}/>}>{'\u0648\u0631\u0648\u062f \u0628\u0647 Negin AI'}</Button>
            {showAndroidDownload?<a className="ng-auth-v2__download" href="/download/android"><Download size={17}/><span>{'\u062f\u0627\u0646\u0644\u0648\u062f \u0646\u0633\u062e\u0647 Android'}</span></a>:null}
          </Stack>
        </form>
      </Surface>
    </main>
  )

  return <AuthContext.Provider value={context}>{children}</AuthContext.Provider>
}
