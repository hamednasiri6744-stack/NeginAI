# مالکیت Host، Zoom و Parity ویجت‌های داشبورد (`RPT-03/RPT-04`)

ده Method از `VN.SDS.MainData.UI.dll` با IL ایستا بررسی شد. `RPT-03` پنج نوع widget
را می‌سازد، permission را بررسی می‌کند و Refresh را به widgetها dispatch می‌کند؛
اما در Methodهای shell هیچ Query وجود ندارد. `RPT-04` فقط Control را برای zoom و
drag/drop جابه‌جا می‌کند و مالک Scope، Formula یا Result set نیست.

پس parity مستقل shell کاربرد ندارد. Parity میزبان شامل مجموعه widgetهای مجاز،
شناسه و عنوان، layout، visibility، dispatch Refresh و وضعیت loading/fresh/stale/
failed/unauthorized/empty است. هر پنج child widget باید قرارداد Query، grain، metric
formula، business date و frozen-UAT جدا داشته باشند.

Refresh-all یک transaction یا snapshot اتمیک نیست. هر widget watermark و outcome
خود را دارد و شکست یکی نباید داده چهار widget دیگر را پاک یا retry کور کند. Zoom
باید همان widget id، filter hash و watermark را نشان دهد و بدون درخواست Refresh
صریح Query تازه‌ای نسازد.

شش Golden Case برای permission، شکست جزئی Refresh، watermarkهای متفاوت، zoom، close
و retry ثبت شد. Result parity ویجت‌ها هنوز صفر، Risk count برابر ۸۴ و اجرای Dashboard،
Widget، Query یا Assembly صفر است.
