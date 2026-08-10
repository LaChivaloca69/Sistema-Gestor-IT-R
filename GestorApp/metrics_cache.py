"""Cache de KPIs / badges del sidebar y home (TTL corto)."""

from django.conf import settings
from django.core.cache import cache

VERSION_KEY = "gestor:metrics:version"
DEFAULT_TTL = 45


def metrics_ttl():
    return int(getattr(settings, "METRICS_CACHE_TTL", DEFAULT_TTL))


def metrics_version():
    version = cache.get(VERSION_KEY)
    if version is None:
        cache.add(VERSION_KEY, 1, timeout=None)
        version = cache.get(VERSION_KEY) or 1
    return version


def invalidate_metrics_cache():
    """Invalida badges/KPIs cacheados (bump de version)."""
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 1, timeout=None)
    return metrics_version()


def _user_cache_key(prefix, user):
    user_id = getattr(user, "pk", None) or "anon"
    return f"{prefix}:v{metrics_version()}:u{user_id}"


def get_or_set_user_metric(prefix, user, builder):
    """Obtiene metrica cacheada por usuario o la calcula y guarda."""
    if not user or not getattr(user, "is_authenticated", False):
        return builder()

    key = _user_cache_key(prefix, user)
    cached = cache.get(key)
    if cached is not None:
        return cached

    value = builder()
    cache.set(key, value, metrics_ttl())
    return value
