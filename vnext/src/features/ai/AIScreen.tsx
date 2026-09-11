import { Mic, Paperclip, Send, Sparkles } from 'lucide-react'

export function AIScreen() {
  return (
    <div className="ng-screen" data-trace-id="SCR-S2-01">
      <section className="ng-ai-hero">
        <span className="ng-ai-orb" data-trace-id="CMP-SPEC-002"><Sparkles /></span>
        <div>
          <span className="ng-eyebrow">AI Assistant</span>
          <h1>دستیار هوشمند داخل NeginAI</h1>
          <p>AI از Capabilityها، Semantic Contractها و ابزارهای مجاز محصول استفاده می‌کند؛ نه از UI یک اپ خارجی.</p>
        </div>
      </section>

      <section className="ng-ai-empty">
        <strong>یک کار یا سؤال سازمانی را شروع کنید</strong>
        <span>پاسخ‌های عددی قطعی فقط پس از اتصال به Evidence و Semantic Source معتبر نمایش داده می‌شوند.</span>
      </section>

      <form className="ng-composer" data-trace-id="CMP-SPEC-006" onSubmit={(event) => event.preventDefault()}>
        <button type="button" className="ng-icon-button" aria-label="افزودن فایل"><Paperclip size={19} /></button>
        <textarea rows={1} aria-label="پیام به دستیار" placeholder="از NeginAI بپرسید…" />
        <button type="button" className="ng-icon-button" aria-label="ورودی صوتی"><Mic size={19} /></button>
        <button type="submit" className="ng-send-button" aria-label="ارسال"><Send size={18} /></button>
      </form>
    </div>
  )
}
