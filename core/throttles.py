from rest_framework.throttling import BaseThrottle
from django.core.cache import cache
from rest_framework.exceptions import Throttled

class LoginRateLimitThrottle(BaseThrottle):
    def get_ident(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def allow_request(self, request, view):
        ip = self.get_ident(request)
        key = f"rate-limit:login:{ip}"
        count = cache.get(key)
        if count is not None and int(count) >= 5:
            raise Throttled(detail="Too many failed login attempts. Please try again after 15 minutes.")
        return True

    @classmethod
    def record_failed_attempt(cls, ip_address):
        key = f"rate-limit:login:{ip_address}"
        # Set value to 1 with 900s TTL if key doesn't exist, else increment
        added = cache.add(key, 1, timeout=900)
        if not added:
            cache.incr(key)

    @classmethod
    def clear_attempts(cls, ip_address):
        key = f"rate-limit:login:{ip_address}"
        cache.delete(key)
