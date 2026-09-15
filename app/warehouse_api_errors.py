"""JSON failures and private tracebacks for the dedicated warehouse worker."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4
from starlette.responses import JSONResponse


def install_error_handler(app, log_path):
    logger=logging.getLogger('warehouse.api.errors')
    logger.propagate=False
    if not logger.handlers:
        handler=RotatingFileHandler(Path(log_path),maxBytes=2_000_000,backupCount=2,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        logger.addHandler(handler)
    logger.setLevel(logging.ERROR)

    async def unexpected_error(request, exc):
        reference=uuid4().hex[:12]
        logger.error('reference=%s path=%s',reference,request.url.path,exc_info=(type(exc),exc,exc.__traceback__))
        return JSONResponse(status_code=500,content={'detail':f'خطای داخلی سرویس انبار؛ شناسهٔ پیگیری: {reference}'})
    app.add_exception_handler(Exception,unexpected_error)
