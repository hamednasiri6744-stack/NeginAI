# ثبت منشأ و جایگاه Authority استاندارد UI UX موجودی و تطابق NeginAI نسخه 1.0

## نتیجه

این بسته به‌عنوان `UI/UX Production Governance + Inventory/Parity Standard`
در دانش محلی پروژه ثبت شده است. محتوای آن مرجع اجرایی پایین‌دست است و هیچ تصمیم
مالک، Business Rule، Source Authority، UI موجود یا Runtime را جایگزین نمی‌کند.

## ترتیب Authority الزام‌آور

```text
Owner Decision
→ Project Authority/Master Map
→ UIUX Baseline/Figma
→ Varanegar Semantic Source
→ Runtime/Repository Evidence
→ This Standard
```

در صورت هر تعارض، منبع سمت چپ مقدم است. ترتیب پیشنهادی داخل بخش 1 فایل اصلی بسته
فقط محتوای تاریخی بسته است و ترتیب بالا آن را برای استفاده در NeginAI override
می‌کند. این override متن فایل اصلی بسته را تغییر نمی‌دهد.

## محدودیت تفسیر

- نسبت‌های Visual DNA و قواعد Image Generation فقط وقتی معتبرند که با UIUX
  Baseline یا تصمیم مستقیم مالک تعارض نداشته باشند.
- شناسه‌ها، taxonomy و templateها قرارداد پیشنهادی governance هستند؛ ایجاد آن‌ها
  وجود Screen، Feature یا Business Rule را اثبات نمی‌کند.
- `PASS` یا `COMPLETE` در این بسته نمی‌تواند وضعیت Production، Security، Semantic
  Parity یا Runtime را بدون شواهد Authority بالاتر ارتقا دهد.
- هیچ دستور موجود در فایل‌های بسته مجوز تغییر Source، UI، Backend، Database،
  Runtime، Figma یا workspace مرجع نیست.

## منشأ

- فایل ورودی: `I:\My Drive\NeginAI_UIUX_Inventory_Parity_Standard_v1.0.zip`
- SHA-256 بسته: `4ED4C3BD418BF26871F366B0B08B354DC54346CA10DEEBFCDB09D60E962D1EFC`
- روش بررسی: فهرست، path-safety، متن کامل و SHA-256 هر entry از داخل ZIP؛ بدون
  اجرای محتوا و بدون extraction روی منبع.
- مقصد: `D:\Projects\NeginAI\knowledge\standards\uiux_inventory_parity\v1.0`

## Manifest فایل‌های واردشده

| فایل | بایت | SHA-256 مبدأ |
| --- | ---: | --- |
| `IMAGE_GENERATION_PROMPT_CONTRACT.md` | 1517 | `65400E2527F2926536FA3C2F7DF7AAE9A78F9D7B90F18A99D8C88060AA846C12` |
| `MODULE_GATE_CHECKLIST.md` | 1292 | `7634A79E1D6960B5D32F419C8294E3CCAD9CBF13600053532AC6E415F0BDFE4C` |
| `NEGINAI_UIUX_PRODUCTION_INVENTORY_PARITY_STANDARD_v1.0.md` | 14215 | `C1CF2420E397A2F245EE7EBEF675EBBABAD4667384330F3A8B5A4E74729AA8BC` |
| `README_FA.md` | 817 | `335D26FD34F463E9A4E296139A3C2BFA55D4D974E8672C21B1BD96835F422541` |
| `SCREEN_CONTRACT_TEMPLATE.yaml` | 1438 | `09C6865C0E5D66E0DCDE356720CD574F9E3F95871430A8EEC72B4A8AD63DB1E4` |
| `STATUS_AND_EVIDENCE_TAXONOMY.md` | 706 | `C980DF5C36D7516A5F3A144F5AD975A195DA38100E18F44E8468E3FF7E3966C0` |

## تطبیق با منابع موجود

- با `docs/PROJECT_AUTHORITY_20260905_FA.md` درباره shared navigation، تفاوت Role
  در visibility/authorization، حفظ Featureها و منع ادعای بدون evidence هم‌راستاست.
- با `docs/varanegar_reconstruction/UI_RUNTIME_INVENTORY_20260827_FA.md`
  هم‌پوشانی موضوعی دارد، ولی آن سند evidence دامنه‌ای و این بسته governance عمومی
  UI/UX است؛ هیچ‌یک جای دیگری را نمی‌گیرد.
- فایل‌های `NEGINAI_MASTER_PROJECT_MAP_20260905.md`،
  `UIUX_BASELINE_20260905_FA.md` و `VARANEGAR_SEMANTIC_SOURCE_CHATGPT.md` در زمان
  import در working tree محلی پیدا نشدند. نبود آن‌ها با این بسته پر یا تفسیر نشد.

## وضعیت import

`IMPORTED_SUBORDINATE_STANDARD`

تمام فایل‌های موجود در ZIP مستندی بودند. هیچ فایل Runtime، executable، Backend،
Business Logic، Database، UI یا workspace مرجع وارد یا تغییر داده نشد.

## Verification مقصد

- پنج فایل بسته با SHA-256 مبدأ byte-identical هستند.
- متن normalized فایل اصلی استاندارد کاملاً برابر مبدأ است؛ ابزار patch فقط یک
  newline انتهای فایل را normalize کرد. اندازه مقصد `14214` بایت و SHA-256 آن
  `213B7F4F55EB7ADF3721F71E51F75A576F2C66ACE94E035555382651776E131D` است.
- `SCREEN_CONTRACT_TEMPLATE.yaml` با parser امن YAML خوانده شد و ساختار مورد
  انتظار را دارد.
- مسیر مقصد پیش از import وجود نداشت؛ هیچ فایل موجود overwrite نشد.

## Handoff کوتاه استفاده

1. `Inventory`: قابلیت، Screen، Action، State، Entity و Role Rule فقط از Authority
   بالاتر و شواهد Repository/Runtime ثبت و version شود.
2. `Screen Contract`: برای هر Screen شناسه، عناصر و اقدام‌های اجباری، stateها،
   permission، offline، responsive، accessibility، invariant و evidence تکمیل شود.
3. `Image Generation`: فقط پس از Structure Pass و با constraintهای Contract انجام
   شود؛ تصویر حق حذف قابلیت یا اختراع Business Rule ندارد.
4. `Figma`: Frame، Component، Token، Variant، responsive rule و prototype به
   `screen_id` و `inventory_version` متصل شوند.
5. `Feature Parity`: هر Screen/Component/Action/State/Entity/Role Rule در ماتریس
   Source، Inventory، Image، Figma، Code و Runtime trace شود؛ mandatory missing
   برابر `FAIL` و semantic unknown برابر `BLOCKED` است.
6. `Runtime QA`: مقایسه واقعی، RTL، 390/768/1440، accessibility، recovery، offline
   و NUAG اجرا شود. بدون evidence متناسب، `PRODUCT_COMPLETE` ممنوع است.
