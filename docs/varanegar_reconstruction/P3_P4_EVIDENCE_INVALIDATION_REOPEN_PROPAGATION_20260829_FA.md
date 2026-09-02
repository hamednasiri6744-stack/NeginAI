# گراف Invalidation و بازشدن Gateهای شواهد P3/P4

تاریخ: ۲۰۲۶-۰۸-۳۱

## هدف

این بسته اثر fail-closed انقضا، revoke، supersession و drift شواهد را از Custody تا Handoff، Adapter، Receipt slot، Promotion Guard و CG-05 مدل می‌کند. هیچ رخداد واقعی مشاهده یا ایجاد نشده است.

## پوشش

- دوازده علت Invalidation برای ۵۴ Custody requirement، یعنی ۶۴۸ assignment؛
- ۵۴ Edge از requirement به Capture Pair؛
- ۵۴ Edge از requirement به Adapter Profile؛
- ۵۴ Edge از requirement به Receipt slot؛
- ۹۶ Edge از هشت Pair به دوازده Promotion Guard؛
- ۲۷ Edge از Receipt slot به Packet؛
- در مجموع ۲۸۵ Edge وابستگی و هشت Reopen action.

علت‌ها انقضا/revoke مجوز Capture، رد/انقضای Redaction، انقضا/revoke/supersede Custody، شکست زنجیرهٔ hash، drift در Manifest/Case، Policy، Adapter/Profile، اصالت Receipt و اختلاف نتیجهٔ تازه را پوشش می‌دهند.

## قاعدهٔ Fail-Closed

هر علت باید Custody را non-current، Gateهای Handoff را باز، Request در انتظار Adapter را cancel/quarantine، Receipt وابسته را invalidate، Promotion Guard را باز و CG-05/UAT/Readiness را Block کند. Recapture، Replay، Repair یا Reacceptance خودکار ممنوع است و شاهد تازه و داوری مستقل لازم است.

## وضعیت فعلی

- همهٔ ۶۴۸ assignment در `NO_EVENT_OBSERVED` هستند.
- Observed invalidation، Custody invalidated، Handoff reopened، Adapter invalidated، Receipt/Guard reopened و Evidence reaccepted همگی صفرند.
- Result parity، CG-05 closure و Readiness صفر است.
- هیچ اتصال، اجرا، Mutation، Payload یا دادهٔ حساس استفاده نشده و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

