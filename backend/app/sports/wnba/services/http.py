"""Paylasilan HTTP oturumu — OS sertifika deposunu kullanir (Windows uyumlu)."""
from __future__ import annotations

import ssl

import requests

_DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; WNBADataCollector/1.0)",
}


def _default_ssl_context() -> ssl.SSLContext:
    """Python 3.12+ Windows'ta sistem CA deposunu kullanir."""
    return ssl.create_default_context()


def make_requests_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(_DEFAULT_HEADERS)
    # certifi bundle yerine OS native CA store (kurumsal proxy/sertifika uyumu)
    session.verify = True
    # requests adapter'a ozel context bagla
    adapter = requests.adapters.HTTPAdapter()
    session.mount("https://", _SSLAdapter())
    return session


class _SSLAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = _default_ssl_context()
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs["ssl_context"] = _default_ssl_context()
        return super().proxy_manager_for(proxy, **proxy_kwargs)
