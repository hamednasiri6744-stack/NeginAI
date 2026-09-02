# مرز Selector و Routing گزارش‌های انبار (`RPT-16/RPT-17`)

بررسی IL ایستای `VN.SDS.Stock.UI.dll` نشان داد این دو Surface گزارش داده‌ای مستقل
نیستند. `RPT-16` فقط یک modal selector برای انتخاب نوع کالا است و با DialogResult
قبول/لغو می‌شود. `RPT-17` enum گزارش‌ها را با resource عنوان می‌سازد، انتخاب rowها
را می‌خواند و امکان route به `RPT-14` یا `RPT-15` را دارد. در شش Method منتخب هیچ
Query مشاهده نشد.

بنابراین Gap «Result parity مستقل» برای این دو بازتعریف شد: خود selector result set
ندارد؛ parity لازم، outcome انتخاب، mapping enum/resource، انتقال Scope و route درست
است. Result parity داده به قرارداد پایین‌دستی `RPT-14` یا `RPT-15` تعلق دارد.

ERP مقصد باید شناسه enum پایدار را از عنوان محلی جدا کند، enum ناشناخته یا resource
گمشده را fail-closed کند، و AccYear/DC/Goods/Stock/date/type را بدون widening منتقل
کند. اگر چند route انتخاب شد، outcome هر مسیر جداست و شکست یکی موفقیت دیگری را پاک
نمی‌کند. هر گزارش پایین‌دستی مجوز مستقل دارد.

شش Golden Case برای cancel، انتخاب کالا، enum ناشناخته، route به هر گزارش و partial
failure چندمسیره ثبت شد. Risk تازه ساخته نشد، شمار ریسک ۸۴ است و هیچ Dialog، فرم،
گزارش، Query یا Assembly اجرا نشد.
