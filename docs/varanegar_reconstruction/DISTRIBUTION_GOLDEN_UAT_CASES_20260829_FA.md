# Golden/UAT توزیع — ۱۴۰۵/۰۶/۰۷

برای چهار فرمان توزیع ۲۸ case طراحی شد: denial، stale version، duplicate command id، fault injection، scope، success و یک حالت ویژه برای هر فرمان.

حالت‌های ویژه number/history fork، late cardex check پس از Issue، مالک transaction نامعلوم Merge و partial cleanup در Remove را پوشش می‌دهند. Outcome ناشناخته و failure همراه اثر durable صریحاً نیازمند read-back یا اثبات rollback هستند.

تمام caseها `DESIGNED_NOT_EXECUTED` هستند؛ runtime، command-ready، pilot-ready و owner approval صفر است.
