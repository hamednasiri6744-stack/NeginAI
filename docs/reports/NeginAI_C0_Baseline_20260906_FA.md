# گزارش C0 هویت Release و Baseline پروژه NeginAI — 2026-09-06

## وضعیت

**PARTIAL / BLOCKED_DIRTY_TREE**

این گزارش فقط وضعیت محلی `D:\Projects\NeginAI` را ثبت می‌کند. در تهیه آن هیچ
فایل، سرویس یا داده‌ای در `\\192.168.1.184\NeginAI` خوانده یا تغییر داده نشد و
هیچ commit، remote، upstream، deploy یا sync ساخته نشد.

## هویت اثبات‌شده

| معیار | نتیجه |
| --- | --- |
| ریشه Git | `D:\Projects\NeginAI` |
| Branch | `dev/hamed` |
| HEAD | `673112f6ce5bb1f8dfaca41804cbd893b57bfc6c` |
| Detached HEAD | خیر |
| Remote | ندارد |
| Upstream | ندارد |
| تصمیم C0 | `BLOCKED_DIRTY_TREE` |

## طبقه‌بندی live working tree

خروجی ابزار `tools/security/release_baseline.py` بلافاصله پیش از افزودن خود این
گزارش به working tree:

| معیار | تعداد |
| --- | ---: |
| کل تغییرها | 361 |
| staged | 0 |
| tracked و unstaged | 59 |
| untracked | 302 |
| unmerged | 0 |
| configuration | 11 |
| documentation | 236 |
| source | 64 |
| test | 40 |
| unclassified | 6 |
| suspicious artifact name | 4 |

چهار نام غیرعادی زیر فقط برای triage ثبت شده‌اند و حذف یا اصلاح نشده‌اند:

- `!j.includes(id))`
- `1`
- `2`
- `clock_timestamp(),','                    (lease_seconds, command.command_id, command.worker_id, command.attempt_count),','                )','                if cursor.rowcount != 1`

وجود نام غیرعادی به‌تنهایی اثبات نمی‌کند که فایل زائد یا قابل حذف است. تصمیم حذف
نیازمند بررسی محتوا، provenance و درخواست صریح مالک پروژه است.

## ابزار قابل تکرار

```powershell
Set-Location D:\Projects\NeginAI
.\.venv\Scripts\python.exe tools\security\release_baseline.py .
```

قرارداد exit code:

- `0`: `READY_CLEAN_HEAD`
- `1`: baseline معتبر Git وجود دارد، اما release به‌علت dirty tree یا نبود commit مسدود است.
- `2`: خطای ورودی، Git یا parsing؛ جزئیات حساس چاپ نمی‌شود.

خروجی شامل نام remote است، اما URL remote را عمداً ثبت نمی‌کند تا credential
احتمالی داخل URL افشا نشود. timestamp و مسیر absolute نیز در JSON نیستند؛ بنابراین
برای یک وضعیت Git ثابت، خروجی machine-readable پایدار می‌ماند.

## شواهد تازه

- `tests/test_release_baseline.py`: دو تست موفق؛ clean identity، عدم افشای remote
  URL، dirty-tree classification و fail-closed decision را پوشش می‌دهد.
- تست‌های ابزار baseline و release-tree guard: `4 passed`.
- سه شکست محصولی تاریخی در اجرای هدفمند تازه بازتولید نشدند: مجموعه تست startup
  همزمان SQLite، پایان visit با saved request و قرارداد port در مجموع `5 passed`.
- مجموعه 59 فایل top-level محصول با حذف فایل‌های تاریخی `test_varanegar*`:
  `445 passed` و exit code صفر. این اجرا پوشه‌های فرعی load/provider/UI و کل suite
  تاریخی را شامل نمی‌شود.
- سه تست JavaScript handoff (`grouped catalog`، `order voice` و `invoice units`):
  `3 passed`.
- TypeScript UI check با `tsc --noEmit`: موفق.
- بررسی `release_tree_guard` روی archive موقت واقعی HEAD اجرا نشد، چون عملیات
  ساخت/پاک‌سازی پوشه موقت توسط policy محیط رد شد؛ تست واحد guard موفق است، اما
  این دو سطح verification معادل نیستند.
- ESLint روی `app/static/assistant.js`: ناموفق با `42 error` و `49 warning`؛ از
  جمله undefined variable، redeclaration، unreachable code و empty block.
- Stylelint روی CSSهای static: ناموفق با `3888 error`؛ بخش بزرگی از خروجی به
  قالب فشرده تک‌خطی CSS و قواعد formatting مربوط است. هیچ auto-fix اجرا نشد.
- اجرای CLI روی working tree واقعی: exit code برابر `1` و تصمیم
  `BLOCKED_DIRTY_TREE` با 361 تغییر.
- compile هدفمند Python موفق بود.
- `ruff` در virtual environment نصب نیست؛ lint این slice اجرا نشد.
- pytest پس از موفقیت تست‌ها، هنگام cleanup سراسری temp یک هشدار
  `PermissionError` برای `pytest-current` ثبت کرد؛ exit code خود pytest برابر صفر
  بود و این هشدار به assertionهای slice مربوط نبود.

## شکاف Authority

`docs/PROJECT_AUTHORITY_20260905_FA.md` فایل
`NEGINAI_MASTER_PROJECT_MAP_20260905.md` را Master Baseline فعال معرفی می‌کند، اما
این فایل با جست‌وجوی نام در working tree محلی پیدا نشد. محتوای آن نباید از روی
handoffهای قدیمی حدس زده شود. تا بازیابی یا تحویل نسخه معتبر آن، Authority کامل
برای C0 در وضعیت `PARTIAL` است.

## Gateهای باقی‌مانده C0

1. بازیابی و بررسی نسخه معتبر `NEGINAI_MASTER_PROJECT_MAP_20260905.md` در فضای
   محلی، بدون import خودکار از share شبکه‌ای.
2. تعیین provenance و disposition برای 361 تغییر موجود؛ هیچ reset، clean یا حذف
   خودکار مجاز نیست.
3. تعیین مجموعه دقیق source/release candidate و اجرای `release_tree_guard` روی
   همان artifact واقعی، نه روی پوشه توسعه دارای runtime data.
4. اجرای کل suite شامل تست‌های تاریخی و پوشه‌های فرعی و ثبت شکست‌های product در
   برابر شکست‌های محیطی؛ subset اصلی top-level اکنون سبز است.
5. triage خطاهای ESLint بر اساس اثر runtime و سپس تعیین baseline/format policy
   برای Stylelint؛ تغییر انبوه یا auto-fix بدون بررسی مجاز نیست.
6. تکمیل lockfile، build تکرارپذیر، migration policy، SBOM و تمرین restore طبق
   Gate فعال پروژه.

تا بسته‌شدن این موارد، وضعیت Commercial/Enterprise همچنان `NO-GO` است.
