import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { CheckCircle2, Download, LockKeyhole, LogIn, UserRound, WifiOff } from 'lucide-react'
import {
  Alert,
  AuthPattern,
  AuthStatusPattern,
  Button,
  PasswordInput,
  Spinner,
  Stack,
  StatusBadge,
  Text,
  TextInput,
} from '../../design-system/v2'
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
    if(!isOnline){setError('اتصال شبکه برقرار نیست.');return}
    if(!cleanUsername||!password){setError('نام کاربری و رمز عبور را وارد کنید.');return}
    setPending(true);setError('')
    try{
      const value=await apiRequest<AuthProfile>('/auth/login',{method:'POST',body:{username:cleanUsername,password}})
      clearApiQueryCache();setProfile(value);setState('success');window.setTimeout(()=>setState('authenticated'),360)
    }catch(reason){
      setError(reason instanceof ApiError&&reason.status===401
        ?'نام کاربری یا رمز عبور اشتباه است.'
        :reason instanceof ApiError&&(reason.kind==='network'||reason.kind==='timeout')
          ?'ارتباط با سرور برقرار نشد.'
          :reason instanceof Error?reason.message:'خطا در ورود.')
    }finally{setPending(false)}
  }

  async function logout(){
    try{await apiRequest('/auth/logout',{method:'POST'})}
    finally{clearApiQueryCache();setProfile(null);setPassword('');setState('anonymous')}
  }

  const context=useMemo(()=>({profile,logout}),[profile])

  if(state==='checking')return (
    <AuthStatusPattern>
      <Stack gap={4}>
        <Spinner label="در حال بررسی نشست"/>
        <Text as="strong" variant="card">در حال بررسی نشست...</Text>
      </Stack>
    </AuthStatusPattern>
  )

  if(state==='success')return (
    <AuthStatusPattern>
      <Stack gap={4}>
        <CheckCircle2 size={36}/>
        <StatusBadge label="ورود موفق" tone="success"/>
        <Text variant="secondary">در حال ورود به Negin AI...</Text>
      </Stack>
    </AuthStatusPattern>
  )

  if(state==='anonymous')return (
    <AuthPattern
      title="ورود به سامانه"
      description="برای ادامه، اطلاعات حساب سازمانی خود را وارد کنید."
      footer={showAndroidDownload ? (
        <a className="ng-auth-pattern__download" href="/download/android">
          <Download size={17}/><span>دانلود نسخه Android</span>
        </a>
      ) : undefined}
    >
      <form onSubmit={login} aria-busy={pending}>
        <Stack gap={5}>
          {!isOnline?<Alert title="آفلاین" tone="offline"><WifiOff size={16}/> اتصال شبکه برقرار نیست.</Alert>:null}
          {error?<Alert title="ورود ناموفق" tone="danger">{error}</Alert>:null}
          <TextInput
            id="username"
            label="نام کاربری"
            leading={<UserRound size={18}/>}
            value={username}
            onChange={e=>{setUsername(e.target.value);if(error)setError('')}}
            autoComplete="username"
            disabled={pending}
            required
          />
          <PasswordInput
            id="password"
            label="رمز عبور"
            leading={<LockKeyhole size={18}/>}
            value={password}
            onChange={e=>{setPassword(e.target.value);if(error)setError('')}}
            autoComplete="current-password"
            disabled={pending}
            required
          />
          <Button type="submit" size="lg" loading={pending} disabled={!isOnline} startIcon={<LogIn size={18}/>}>ورود به Negin AI</Button>
        </Stack>
      </form>
    </AuthPattern>
  )

  return <AuthContext.Provider value={context}>{children}</AuthContext.Provider>
}
