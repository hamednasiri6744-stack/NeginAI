# تنظیم Action برای هوش مصنوعی نگین پخش

آدرس عمومی پایدار:

`https://ai.neginpakhsh.com`

1. در GPT Builder به `Configure > Actions > Create new action` بروید.
2. در Authentication گزینه `API Key` را انتخاب کنید.
3. نوع کلید را `Custom` و نام Header را `X-API-Key` بگذارید.
4. مقدار `NEGIN_ACTION_API_KEY` را مستقیماً از فایل `.env` در فیلد Secret وارد کنید. کلید را در چت یا Instructions ننویسید.
5. محتوای فایل `openapi-action.yaml` را در Schema وارد کنید.
6. محتوای `docs/custom-gpt-instructions-fa.md` را در Instructions قرار دهید.
7. قابلیت Web Search را روشن نگه دارید؛ دستورهای GPT تضمین می‌کنند سؤال‌های داخلی و اتوماسیون‌ها فقط به Action نگین پخش بروند و وب فقط برای سؤال‌های عمومی استفاده شود.
8. ابتدا اکشن `getHealth` و سپس `chatWithNeginAI` را با سؤال‌های «فروش امروز را اعلام کن» و «هر روز ساعت ۹:۲۰ گزارش فروش امروز را بده» در Preview آزمایش کنید.

## احراز هویت OAuth کاربران

- Authentication type: OAuth
- Client ID: `neginai-chatgpt`
- Authorization URL: `https://ai.neginpakhsh.com/oauth/authorize`
- Token URL: `https://ai.neginpakhsh.com/oauth/token`
- Scope: `company.read`
- Client secret: مقدار `NEGIN_OAUTH_CLIENT_SECRET` در فایل `.env` سرور؛ آن را در گفتگو یا مستندات عمومی قرار ندهید.
- پس از ذخیره Authentication، GPT را Update کنید. اولین گزارش داخلی باید دکمه Sign in نمایش دهد.
9. پس از ذخیره، حتماً `Update` یا `Publish` را بزنید تا نسخه لینک عمومی نیز به‌روزرسانی شود.

## نکته مهم

دامنه `ai.neginpakhsh.com` ثابت است، اما رایانه و سرویس NeginAI باید روشن و به شبکه متصل باشند تا Action و اتوماسیون‌ها اجرا شوند.
