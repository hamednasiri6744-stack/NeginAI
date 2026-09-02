# مرز DataAccess و سطح SQL افزونه‌های مادی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS — Catalog فقط‌خواندنی و تحلیل آفلاین؛ مسیر اجرای SQL هنوز Candidate**

## پاسخ معماری

Legacy در شش Capability از دوازده مسیر منتخب، UI را مستقیم به DataAccess وصل
می‌کند. این اتصال در مقصد نباید بازتولید شود:

| طبقه Legacy | تعداد Capability | نمونه |
|---|---:|---|
| UI مالک `Commit` صریح | ۲ | ArticleTemplate، GeneralConfig |
| UI مالک DataContext بدون Commit مشاهده‌شده | ۲ | WebServiceConfig، POSSession |
| UI دارای Lookup/Read مستقیم DataAccess | ۲ | ChargeDevice، POSSafe |
| بدون Direct UI→DA در مسیر منتخب | ۶ | StockAccess، Instalment، Discount، Subscriber، دو Tablet |

در مجموع ۱۶ Method UI و ۲۶ Edge یکتای Direct-DA ثبت شد. این شاهد Coupling را
ثابت می‌کند، اما نام Read-like اثبات نمی‌کند که Hook یا Dynamic SQL پنهان وجود
ندارد.

## شواهد مهم Clone

Extractor فقط به Clone محلی `NeginPakhsh_WebDev` وصل شد و پیش از Catalog query
موارد زیر را کنترل کرد:

- Database برابر `READ_ONLY`؛
- `can_update=0`؛
- عضویت در `db_denydatawriter=1`؛
- بدون Select از مقدارهای ردیف تجاری، بدون اجرای Procedure/Trigger و بدون ذخیره
  Definition یا Credential.

نتیجه Name-match Catalog برای ۱۲ Capability:

- هر ۱۲ Capability حداقل یک Candidate دارد؛ سه Gap نخست با IL عمیق‌تر و Search
  term دقیق‌تر حل شد؛
- ۱۳۲ Object candidate شامل ۲۸ Table و ۱۰۴ Module/View/Trigger؛
- ۸۲۶ Column metadata، ۶۴ FK، ۴۰ Trigger و ۴۷۵ Dependency ثبت شد.

Name-match فقط Candidate است و مسیر UI→Adapter→SQL را ثابت نمی‌کند.

## Anchorهای با نام قوی

| Capability | Object | Snapshot row count | PK | نکته |
|---|---|---:|---|---|
| Article template | `dbo.ArticleTemplate` | ۰ | `Id` | ۱۶ ستون و چهار Trigger؛ صفر بودن Clone به معنی عدم استفاده Operational نیست |
| General config | `GNR.tblGeneralConfig` | ۱۷۷ | `KeyName` | پنج Trigger |
| General config history | `GNR.tblGeneralConfig_History` | ۸٬۷۸۲ | `ID` | تاریخچه جدا، مؤید Version/Audit requirement |
| Web-service config | `dbo.usp_sdsnet_WebConfigSetting_Save` | — | — | Procedure candidate با دو Dependency؛ Definition ذخیره نشد |
| Charge device | `dbo.BaseChargeDevice` | ۰ | `Id` | ۲۰ ستون و پنج FK؛ Operational freshness نامشخص |
| Instalment | `dbo.InstalmentMethod` | ۰ | `Id` | دو FK |
| Linear discount | `dbo.POSLineDiscount` | ۰ | `Id` | هفت FK و سه Trigger؛ IL تولید ID با `MAX(Id)+1` را نشان داد |
| POS Safe | `dbo.POSSafe` | — | — | View به‌علاوه Procedureهای Save/Delete/Open-safe candidate |
| POS Session send | `dbo.usp_ReplicateSalesReceipt` | — | — | ۶۶ Dependency و شاهد `ExecuteNonQuery`/Transaction در Adapter |
| Subscriber | `dbo.Subscriber` | ۰ | `Id` | سه FK و پنج Trigger |
| Dealer day path | سه `USP_SDSNET_DealersDayPath*` | — | — | Save/List candidate؛ مسیر Base-class هنوز نیازمند اثبات مستقیم |
| Visit template | `NGT.VisitTemplates` و Path tables | ۵۰۷ / چند Ledger مسیر | `Id` | چند مدل FRU/NGT/dbo؛ مالکیت نهایی نیازمند Crosswalk |

Row countها Metadata همان Clone هستند، نه حقیقت زنده سیستم عملیاتی.

## قرارداد مقصد

1. Web UI فقط Input/Result دارد و DataContext/Repository/Commit نمی‌شناسد.
2. Application service مجوز Scope، Validation، Idempotency و Transaction را
   مالک است.
3. Domain invariant مستقل از Infrastructure commit باقی می‌ماند.
4. Infrastructure فقط Repository/Projection محدودشده ارائه می‌کند و Unit of
   Work را از Application service می‌گیرد.
5. برای هر Candidate، قبل از Freeze باید Adapter IL، ORM mapping یا dependency
   رسمی مسیر دقیق SQL را ثابت کند.

## فایل‌ها

- Catalog machine evidence:
  `artifacts/varanegar_analysis/ui/varanegar_extension_sql_surface_20260827.json`
- Boundary assessment:
  `artifacts/varanegar_analysis/ui/varanegar_extension_data_boundary_assessment_20260827.json`
- Extractor:
  `scripts/sql/extract_varanegar_extension_sql_surface.py`
- Builder:
  `scripts/windows/build_varanegar_extension_data_boundary_assessment.py`
- Deep gap trace:
  `artifacts/varanegar_analysis/ui/varanegar_extension_gap_paths_20260827.json`
