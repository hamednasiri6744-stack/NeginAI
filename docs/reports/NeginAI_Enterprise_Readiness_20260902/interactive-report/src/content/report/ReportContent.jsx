import React from "react";

import {
  DataComponent,
  DataTable,
  MetricCard,
  ReportSection,
  RichNarrative,
  useDataApp,
} from "../../data-app-public.jsx";

const inventoryColumns = [
  { key: "metric", label: "شاخص" },
  { key: "value", label: "مقدار", align: "right" },
];
const testColumns = [
  { key: "suite", label: "مجموعه آزمون" },
  { key: "passed", label: "موفق", align: "right" },
  { key: "failed", label: "ناموفق", align: "right" },
];
const roadmapColumns = [
  { key: "phase", label: "مرحله" },
  { key: "weeks_min", label: "حداقل هفته", align: "right" },
  { key: "weeks_max", label: "حداکثر هفته", align: "right" },
];
const securityColumns = [
  { key: "id", label: "شناسه" },
  { key: "severity", label: "شدت", presentation: "status" },
  { key: "finding", label: "یافته" },
];

export function ReportContent() {
  const { reviewedPeriodRows, canEdit, mode, appTitle, setAppTitle } = useDataApp();
  const inventory = reviewedPeriodRows("inventory");
  const tests = reviewedPeriodRows("test_results");
  const security = reviewedPeriodRows("security_findings");
  const roadmap = reviewedPeriodRows("roadmap");

  return <article className="report-content" dir="rtl" aria-label="گزارش آمادگی اینترپرایز NeginAI">
    <header className="report-hero">
      <div className="verdict-badge">ارزیابی مستقل · ۱۲ شهریور ۱۴۰۵</div>
      <h1 data-data-app-title contentEditable={canEdit && mode === "edit"} suppressContentEditableWarning
        aria-label={canEdit && mode === "edit" ? "ویرایش عنوان گزارش" : undefined}
        onBlur={canEdit && mode === "edit" ? (event) => setAppTitle(event.currentTarget.textContent.trim() || appTitle) : undefined}
        onKeyDown={canEdit && mode === "edit" ? (event) => {
          if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); }
        } : undefined}>{appTitle}</h1>
      <RichNarrative id="report:description" className="report-deck" label="ویرایش مقدمه"
        value="**نتیجه:** پروژه یک پایه‌ی فنی قابل توسعه دارد، اما نسخه‌ی فعلی برای بهره‌برداری اینترپرایز با ۲۰۰ کاربر همزمان هنوز **NO-GO** است. مسیر پیشنهادی، بازنویسی کامل نیست؛ تثبیت قراردادهای حیاتی و تبدیل تدریجی معماری به هسته‌ی قطعی، APIهای بدون حالت و پردازشگرهای پایدار است." />
    </header>

    <div className="report-facts" aria-label="شاخص‌های کلیدی">
      <MetricCard id="metric-files" title="فایل‌های رهگیری‌شده" queryId="inventory" sourceRows={inventory}
        value="۱٬۸۹۲" description="دامنه‌ی واقعی مخزن در بازبینی فعلی" />
      <MetricCard id="metric-tests" title="آزمون‌های Python موفق" queryId="test_results" sourceRows={tests}
        value="۲٬۴۹۱" comparison="۱۱ شکست" negative description="اجرای کامل، به‌جز یک مانع جمع‌آوری" />
      <MetricCard id="metric-product" title="آزمون محصول" queryId="test_results" sourceRows={tests}
        value="۳۴۸" comparison="۳ شکست" negative description="بدون آزمون‌های تاریخی Varanegar" />
      <MetricCard id="metric-capacity" title="هدف ظرفیت" queryId="roadmap" sourceRows={roadmap}
        value="۲۰۰+" description="کاربر همزمان؛ نیازمند تست بار و SLO اثبات‌شده" />
    </div>

    <ReportSection id="report-verdict" title="حکم اجرایی" queryId="test_results" sourceRows={tests} showHeading={false}>
      <RichNarrative id="report-verdict:body" className="report-analysis" label="ویرایش حکم اجرایی"
        value={`## حکم اجرایی

**پایه‌ی پروژه مناسب ادامه‌دادن است، نه استقرار سراسری.** FastAPI ماژولار، قراردادهای خواندن SQL، ابزارهای دامنه، مسیر موبایل و پوشش آزمون قابل توجه‌اند. با این حال، قفل SQLite در شروع همزمان، قرارداد ناتمام پایان ویزیت/سفارش، اختلاف پورت استقرار، هویت مشترک API و نبود کنترل ظرفیت سراسری مانع پذیرش اینترپرایز هستند.

سه شکست محصول مستقیماً بازتولید شدند: خطای «database is locked» در شروع موازی، رفتار نادرست درخواست ذخیره‌شده هنگام پایان ویزیت، و ناهماهنگی پورت بین تست، Caddy و اجراکننده‌ها.`} />
    </ReportSection>

    <DataComponent id="inventory-table" title="نقشه‌ی عددی مخزن" queryId="inventory" kind="table"
      displayRows={inventory} sourceRows={inventory} description="شمارش تازه از شاخه dev/hamed و بازبینی مسیرهای اصلی.">
      <DataTable rows={inventory} columns={inventoryColumns} caption="شاخص‌های ساختاری مخزن" searchable={false} />
    </DataComponent>

    <DataComponent id="tests-table" title="شواهد آزمون" queryId="test_results" kind="table"
      displayRows={tests} sourceRows={tests} description="نتایج اجرای محلی در ۲ سپتامبر ۲۰۲۶؛ آزمون بار ۲۰۰ کاربر هنوز انجام نشده است.">
      <DataTable rows={tests} columns={testColumns} caption="نتایج آزمون‌های اجراشده" searchable={false} />
    </DataComponent>

    <ReportSection id="report-map" title="نقشه‌ی فعلی" queryId="inventory" sourceRows={inventory} showHeading={false}>
      <RichNarrative id="report-map:body" className="report-analysis" label="ویرایش نقشه پروژه"
        value={`## نقشه‌ی فعلی پروژه

- **رابط‌ها:** وب/PWA با HTML، CSS و JavaScript؛ Android مبتنی بر Compose و WebView؛ نمونه‌ی iOS با SwiftUI.
- **لایه کاربرد:** یک modular monolith در FastAPI با ۱۹ router و ۱۱۰ endpoint.
- **هسته دامنه:** تور و مشتری، پیش‌ویزیت، کاتالوگ و سبد، سفارش، وصول، برنامه‌ریزی، اتوماسیون و چت.
- **داده:** SQLite محلی برای state و warehouse، و SQL Server/Varanegar با مسیرهای عمدتاً فقط‌خواندنی و bridge نوشتنِ خاموش به‌صورت پیش‌فرض.
- **هوش فعلی:** ابزارهای typed، guard برای SQL، semantic/schema sync و اتصال مستقیم به OpenAI؛ هنوز gateway مستقل و هسته‌ی تصمیم‌گیری قطعی کامل نشده است.
- **اجرا:** Caddy و Uvicorn روی ویندوز؛ حلقه‌های پس‌زمینه داخل process برنامه قرار دارند و در چند worker خطر اجرای تکراری دارند.`} />
    </ReportSection>

    <ReportSection id="report-alignment" title="تطبیق دانش" queryId="inventory" sourceRows={inventory} showHeading={false}>
      <RichNarrative id="report-alignment:body" className="report-analysis" label="ویرایش تطبیق دانش"
        value={`## تطبیق دانش افزوده‌شده با واقعیت پروژه

فایل handoff جدید در هدف محصول درست جهت می‌دهد: مدل زبانی باید فقط intent، استخراج ساختاری و نگارش اختیاری را انجام دهد و محاسبه، مجوز، SQL، قیمت‌گذاری و تصمیم نهایی داخل NeginAI بماند. وجود FastAPI، موبایل، SQLite/SQL Server و bridge کنترل‌شده نیز تأیید شد.

اما React/TypeScript/Vite، provider gateway مستقل، موتور قواعد/بهینه‌سازی/پیش‌بینی یکپارچه، verifier سراسری و معماری چندگره‌ای هنوز **هدف آینده** هستند، نه قابلیت موجود. مسیر قدیمی «G:/NeginAI» و بخشی از checkpointهای تاریخی نیز با شاخه فعلی drift دارند و باعث ۹ شکست تاریخی شده‌اند.`} />
    </ReportSection>

    <ReportSection id="report-strengths-risks" title="قوت‌ها و ضعف‌ها" queryId="test_results" sourceRows={tests} showHeading={false}>
      <RichNarrative id="report-strengths-risks:body" className="report-analysis" label="ویرایش قوت‌ها و ریسک‌ها"
        value={`## نقاط قوت

- دامنه‌ی کسب‌وکار و مسیر فروشنده به‌خوبی مستندسازی شده و ۲٬۵۰۲ آزمون Python قابل جمع‌آوری است.
- guard خواندن SQL، rollback، محدودیت ردیف و feature flagهای مستقل برای نوشتن Varanegar، طراحی ایمنی قابل توسعه‌ای ساخته‌اند.
- idempotency و receipt در bridge سفارش وجود دارد و پایه‌ی مناسبی برای outbox رسمی است.
- جداسازی نسخه محلی از مسیر رئیس انجام شده و مخزن محلی remote/upstream ندارد.

## ضعف‌های بحرانی

- SQLite فقط یک writer همزمان دارد؛ خطای قفل در آزمون واقعی نیز دیده شد، بنابراین منبع تراکنشی ۲۰۰ کاربر نمی‌تواند همین شکل بماند.
- API key مشترک هویت کاربران/کلاینت‌ها را در یک principal ادغام می‌کند و disabled user می‌تواند refresh token را ادامه دهد.
- صف پایدار، rate limit و budget سراسری، telemetry توزیع‌شده و آزمون بار وجود ندارد.
- قرارداد رسمی «savedata → receipt → Replicate → Varanegar ID» و بازیابی offline هنوز end-to-end بسته و اثبات نشده است.
- قیمت/امتیاز و تصمیم کسب‌وکار نباید به خروجی مدل وابسته باشند؛ در معماری فعلی اتصال مستقیم مدل هنوز این مرز را به‌صورت سراسری enforce نمی‌کند.`} />
    </ReportSection>

    <DataComponent id="security-table" title="یافته‌های اسکن امنیتی" queryId="security_findings" kind="table"
      displayRows={security} sourceRows={security} description="۱۰ یافته اعتبارسنجی‌شده روی snapshot ثابت: ۵ High، ۴ Medium و ۱ Low.">
      <DataTable rows={security} columns={securityColumns} caption="یافته‌های امنیتی به ترتیب شناسه" searchable={false} />
    </DataComponent>

    <ReportSection id="report-target" title="معماری هدف" queryId="roadmap" sourceRows={roadmap} showHeading={false}>
      <RichNarrative id="report-target:body" className="report-analysis" label="ویرایش معماری هدف"
        value={`## معماری هدف برای ۲۰۰ کاربر همزمان

1. **API بدون حالت:** چند replica از FastAPI پشت reverse proxy؛ session و rate limit مشترک خارج از process.
2. **PostgreSQL:** منبع تراکنشی NeginAI با MVCC، migration کنترل‌شده، row-level security تکمیلی و audit append-only.
3. **Redis + صف پایدار:** idempotency، قفل کوتاه، quota، cache و job queue؛ worker جدا برای sync، forecast، report و ERP write.
4. **هسته هوش داخلی:** semantic catalog، policy engine، محاسبات قیمت و امتیاز، optimizer، forecasting، RAG محلی، planner قطعی و verifier.
5. **AI Gateway:** قرارداد JSON schema، redaction، routing و fallback؛ مدل فقط تشخیص intent، استخراج پارامتر و نگارش نهایی مجاز.
6. **Observability و امنیت:** OpenTelemetry، metric/log/trace، SLO، alert، secrets manager، OAuth/OIDC و مجوز ریزدانه.

این طراحی modular monolith را حفظ می‌کند و فقط workloadهای ناهمزمان و integrationهای پرریسک را از process وب خارج می‌کند؛ بنابراین هزینه و ریسک مهاجرت از microservice‌سازی زودهنگام کمتر است.`} />
    </ReportSection>

    <DataComponent id="roadmap-table" title="نقشه راه اجرایی" queryId="roadmap" kind="table"
      displayRows={roadmap} sourceRows={roadmap} description="برآورد ترتیبی ۱۴ تا ۲۳ هفته؛ چند جریان مستقل می‌توانند با تیم کافی هم‌پوشانی داشته باشند.">
      <DataTable rows={roadmap} columns={roadmapColumns} caption="مراحل تبدیل به نسخه اینترپرایز" searchable={false} />
    </DataComponent>

    <ReportSection id="report-gates" title="دروازه‌های پذیرش" queryId="roadmap" sourceRows={roadmap} showHeading={false}>
      <RichNarrative id="report-gates:body" className="report-analysis" label="ویرایش دروازه‌های پذیرش"
        value={`## دروازه‌های پذیرش نسخه اجرایی

- آزمون بار مستقل با حداقل ۲۰۰ کاربر همزمان و p95 تعریف‌شده؛ بدون خطای قفل، data loss یا سفارش تکراری.
- outage/retry/replay برای SQL Server، NGT و provider مدل؛ هر mutation دارای idempotency key، receipt و reconciliation.
- benchmark حداقل ۳۰۰ درخواست واقعی و فارسی روی providerهای ایرانی؛ انتخاب بر اساس نرخ عبور schema، latency، پایداری و سپس قیمت.
- threat model، ASVS، rotation/revocation هویت، ممیزی مجوز و بازیابی backup در محیط staging.
- canary rollout با kill switch مستقل برای هر مسیر نوشتن و rollback تمرین‌شده.

**نکته هزینه:** گزینه‌های داخلی بررسی‌شده عمدتاً gateway ایرانی به مدل‌های جهانی‌اند، نه لزوماً مدل ایرانی. پلن رایگان برای توسعه مفید است ولی برای تولید ۲۰۰ کاربر ظرفیت و SLA کافی را ثابت نمی‌کند؛ قرارداد نهایی باید پس از benchmark و بررسی DPA/SLA انتخاب شود.`} />
    </ReportSection>

    <RichNarrative id="report:disclosure" className="report-disclosure" label="ویرایش محدودیت‌ها"
      value="این گزارش بر مبنای بازبینی ایستا، اجرای آزمون‌های محلی و اسناد رسمی پروژه تا ۲ سپتامبر ۲۰۲۶ است. محیط زنده، نقش‌های واقعی SQL Server، بار ۲۰۰ کاربر و SLA ارائه‌دهندگان در این ارزیابی عملیاتی اندازه‌گیری نشده‌اند؛ بنابراین ادعای آمادگی تولید نشده است." />
  </article>;
}
