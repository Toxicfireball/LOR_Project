import time
import logging
from django.db import connection

log = logging.getLogger("perf.sql")
# characters/middleware.py
from .audit_context import set_current_request, clear_current_request


class AuditUserMiddleware:
    """
    Captures request.user + request.path so model signals can attach 'changed_by'.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            set_current_request(user, request.path)
        else:
            set_current_request(None, request.path)

        try:
            return self.get_response(request)
        finally:
            clear_current_request()



class _QueryTimer:
    def __init__(self, out):
        self.out = out

    def __call__(self, execute, sql, params, many, context):
        start = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            ms = (time.perf_counter() - start) * 1000.0
            self.out.append((ms, sql, params))

def _safe_params(params):
    if params is None:
        return None
    try:
        s = str(params)
        return s if len(s) <= 300 else (s[:300] + "...<truncated>")
    except Exception:
        return "<unprintable>"

class LogSlowQueriesMiddleware:
    """
    Logs the slowest SQL statements per request.
    Uses execute_wrapper so it works even when DEBUG=False.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        queries = []
        start = time.perf_counter()

        with connection.execute_wrapper(_QueryTimer(queries)):
            response = self.get_response(request)

        total_ms = (time.perf_counter() - start) * 1000.0

        # only log your slow page(s)
        if request.path.startswith("/characters/") and total_ms >= 300:
            queries_sorted = sorted(queries, key=lambda x: x[0], reverse=True)
            sql_total = sum(q[0] for q in queries)
            log.info(
                "%s %s -> %s | %.1fms total | %.1fms SQL | %d queries",
                request.method, request.path, getattr(response, "status_code", "?"),
                total_ms, sql_total, len(queries),
            )
            for ms, sql, params in queries_sorted[:15]:
                log.info("  %.1fms | %s | params=%s", ms, sql, _safe_params(params))

        return response
