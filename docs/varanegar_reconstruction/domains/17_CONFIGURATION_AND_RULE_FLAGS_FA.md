# دامنه ۱۷: تنظیمات چندسطحی و فلگ‌های قواعد کسب‌وکار

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **ساختار و مصرف SQL تأیید شد؛ تقدم Scopeها و مقدار مؤثر هنوز باز است**

## مرز حریم و منبع

- Extractor: `scripts/sql/extract_varanegar_configuration_domain.py`
- Artifact: `artifacts/varanegar_analysis/domains/configuration_and_rule_flags_20260826.json`
- ۱۴ جدول، ۷۶ FK رسمی و ۸۶۶ Consumer بررسی شد.
- هیچ مقدار فعلی/قدیمی تنظیمات، رمز، Token، URL، Path، Host/Application identity،
  مالک Device یا ردیف خام History در Artifact ذخیره نشده است.
- برای Key/Valueها فقط نام Key و شکل کلی مقدار
  (`null`/`boolean_like`/`numeric_like`/`text_like`) ثبت شده است.

## نتیجه اصلی: Configuration یک جدول ساده نیست

```text
General configuration
  GNR.tblGeneralConfig + History

Server/DC configuration
  GNR.tblServerConfig + History
  GNR.tblServerConfigDC

Customer-field policy per DC
  GNR.tblCustConfig + GNR.tblCustConfigDC

NGT/mobile configuration
  NGT.BaseValues / PublicValues
  NGT.DeviceSettings / DeviceSettingKeyTypes / AppSettings

Back-office version/data settings
  dbo.ApplicationSetting / ApplicationSettingData
```

بنابراین مقصد نباید همه را در یک Dictionary بدون Scope بریزد. هر تصمیم باید
مشخص کند مقدار از کدام Scope، با چه نسخه و با چه Rule-setی مؤثر شده است.

## Key/Value و تاریخچه

| Scope | کلید فعال | کلید یکتا | مقدار Null | گروه تکراری |
|---|---:|---:|---:|---:|
| General | ۱۷۷ | ۱۷۷ | ۰ | ۰ |
| Server | ۳۳۴ | ۳۳۴ | ۳ | ۰ |

در مجموع ۵۱۱ Key فعال وجود دارد. Key خالی یا Duplicate group دیده نشد.

| History | ردیف | Key | بازه | بدون تغییر مقدار |
|---|---:|---:|---|---:|
| General | ۸٬۷۸۲ | ۱۲۴ | ۲۰۲۱-۰۱-۱۰ تا ۲۰۲۶-۰۸-۲۲ | ۸٬۶۹۵ |
| Server | ۲۱٬۹۱۴ | ۲۷۱ | ۲۰۱۷-۰۵-۱۰ تا ۲۰۲۶-۰۸-۰۲ | ۲۱٬۱۶۱ |

بیشتر Historyها تغییر معنایی مقدار نیستند؛ احتمالاً Save/Audit event هستند. باید
Event حفظ شود اما هر ردیف به‌عنوان نسخه جدید Rule تلقی نشود. یک Key فقط در
General history و ۳۹ Key فقط در Server history دیده شدند؛ این ۴۰ Key می‌توانند
Retired/Renamed باشند و فعال فرض نمی‌شوند.

## تنظیمات DC و فیلد مشتری

- `tblServerConfigDC`: دو ردیف برای دو DC و Ref یتیم صفر؛
- `tblCustConfig`: ۱۰۲ ردیف، ۵۱ فیلد در دو DC، ۲۸ مورد Mandatory و Ref یتیم صفر؛
- `tblCustConfigDC`: دو Default برای دو DC و Ref یتیم صفر.

Schema امن `tblServerConfigDC` نشان می‌دهد قواعدی مانند دوره مجاز فروش، حداکثر
روز سند باز، کنترل چک، محدودیت ردیف/مبلغ سفارش، کنترل تخفیف، ساخت خودکار رسید،
مرجوعی و موجودی در DC قابل تغییرند. ستون‌های حساس عمداً از Artifact حذف شدند.

## تنظیمات NGT و Device

| موجودیت | ردیف | Removed |
|---|---:|---:|
| BaseValues | ۲۰۸ | ۰ |
| PublicValues | ۳۳۲ | — |
| DeviceSettingKeyTypes | ۲۱۳ | — |
| DeviceSettings | ۴۰ | ۲۳ |
| AppSettings | ۱ | ۰ |

از ۴۰ DeviceSettings، ۲۳ مورد Removed است؛ Query عملیاتی باید حذف‌شده‌ها را
فیلتر کند و نباید ۴۰ ردیف را تنظیمات فعال تلقی کند. فیلدهای GPS، کنترل فاصله،
حداکثر فاصله، نمایش موجودی، مرجوعی با/بدون مرجع، کنترل موجودی و الزام صیاد در
هر ۴۰ ردیف حاضرند؛ MandatoryCustomerVisit در ۳۵ ردیف مقدار دارد. این فقط
Coverage ستون است، نه اعلام مقدار مؤثر.

## شواهد مصرف فلگ‌ها در SQL

تعداد Moduleهایی که نام هر فلگ را مصرف می‌کنند:

| فلگ | Module |
|---|---:|
| AutoOrderConfirm | ۱۶ |
| SettlementPreviousDebtId | ۱۱ |
| ControlStockRetSale_ShowCardex | ۱۰ |
| RChequePayControl / PayDateControl | ۹ / ۹ |
| DiscountControl / MinOrderAmount / MaxOrderAmount | ۷ / ۷ / ۷ |
| OrderRowLimit / RefRetOrder / MaxDay4OpenSale / ValidPeriodOfSales | ۶ برای هرکدام |
| Ngt_InsertReceiptForSaleOffice / NGT_CreatePOrder / ValidPeriodOfFinancial | ۵ برای هرکدام |
| CheckSaleItmStock / AllowFreeReason | ۴ / ۴ |
| EffectVocherWithOutConfirm / AutoGenRetSaleVocher / MaxLimitOfOrderConvertToSale | ۳ برای هرکدام |
| CreateExitWithConfirmStockMan / MatchRetSaleVchNo | ۳ / ۳ |

این Referenceها ثابت می‌کنند فلگ در SQL مصرف شده، اما ترتیب دقیق General، Server،
DC، Device و App را اثبات نمی‌کنند. Clientهای Desktop/Android نیز ممکن است خارج
از dependency metadata همان کلیدها را مصرف کنند.

## قرارداد مدل مقصد

- `ConfigurationDefinition`: نام، نوع، مالک دامنه، حساسیت، Default و Validation؛
- `ConfigurationValue`: Definition، ScopeType، ScopeId و Effective period؛
- `ConfigurationVersion`: نسخه immutable با Actor/Reason؛
- `ConfigurationDecision`: Rule، Scope انتخابی، نسخه و Hash غیرحساس مقدار؛
- `SecretReference`: فقط اشاره به Secret store، نه مقدار رمز در DB/Log؛
- `DevicePolicyAssignment`: اتصال صریح Policy فعال به Device/Personnel/DC؛
- `ConfigurationCrosswalk`: نگاشت General/Server/DC/NGT/App legacy؛
- `ConfigurationAuditEvent`: Save event جدا از Semantic value change.

Resolve باید deterministic باشد و نتیجه شامل `source_scope` و `version_id` شود.
مقدارهای محرمانه نباید در Event، Trace، JSON تحلیلی یا Frontend ظاهر شوند.

## Golden Caseهای لازم

1. کلید General بدون Override؛
2. Server override روی General؛
3. DC override روی Server؛
4. Device policy فعال و Removed؛
5. مقدار Null در برابر نبودن Key؛
6. History save بدون تغییر معنایی؛
7. History-only/retired key؛
8. دو DC با قواعد متفاوت سفارش؛
9. Min/Max order و row limit در مرزها؛
10. AutoOrderConfirm روشن/خاموش؛
11. RCheque/PayDate control با سناریوی رد؛
12. DiscountControl و stock-return cardex؛
13. مقدار Secret با Reference و Redaction؛
14. Rollback به نسخه قبل با Audit؛
15. تصمیمی که Scope و version آن قابل بازتولید است.

## ابهام‌های باز

1. تقدم رسمی General/Server/DC/Device/App و رفتار نبودن/Null.
2. Crosswalk مالک/مرکز برای ۱۷ DeviceSettings حذف‌نشده.
3. مقدار مؤثر فعلی؛ نیازمند استخراج کنترل‌شده و طبقه‌بندی حساسیت، نه Dump عمومی.
4. معنای دقیق Historyهای بدون تغییر مقدار و اینکه کدام UI آن‌ها را می‌سازد.
5. Client-side consumerهای Desktop/Android که در SQL metadata دیده نمی‌شوند.
6. اینکه کدام History-only key بازنشسته، rename یا هنوز توسط Client مصرف می‌شود.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_configuration_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\configuration_and_rule_flags_20260826.json
```
