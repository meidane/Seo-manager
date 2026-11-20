"""کلاینتِ مینیمالِ Search Console API با Service Account (JWT امضاشده با `cryptography` — بدونِ وابستگیِ تازه).
پراکسیِ `GSCAccount.proxy` روی همهٔ درخواست‌ها اعمال می‌شود (برای سرورِ ایران → واسطِ خارج)."""
import base64
import json
import time
from urllib.parse import quote

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from django.core.cache import cache

SCOPE = 'https://www.googleapis.com/auth/webmasters.readonly'
API = 'https://www.googleapis.com/webmasters/v3'


class GSCError(Exception):
    pass


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


class Client:
    def __init__(self, account):
        self.acc = account
        self.cred = account.credentials or {}
        if not self.cred.get('private_key') or not self.cred.get('client_email'):
            raise GSCError('کلیدِ Service Account ثبت نشده یا ناقص است')
        self.s = requests.Session()
        if account.proxy:
            self.s.proxies = {'https': account.proxy, 'http': account.proxy}

    def _token(self):
        key = f'gsc:token:{self.acc.pk}:{self.cred["client_email"]}'
        tok = cache.get(key)
        if tok:
            return tok
        now = int(time.time())
        uri = self.cred.get('token_uri') or 'https://oauth2.googleapis.com/token'
        claims = {'iss': self.cred['client_email'], 'scope': SCOPE, 'aud': uri, 'iat': now, 'exp': now + 3600}
        head = _b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode()) + '.' + _b64(json.dumps(claims).encode())
        pk = serialization.load_pem_private_key(self.cred['private_key'].encode(), password=None)
        jwt = head + '.' + _b64(pk.sign(head.encode(), padding.PKCS1v15(), hashes.SHA256()))
        try:
            r = self.s.post(uri, data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': jwt}, timeout=30)
        except requests.RequestException as e:
            raise GSCError(f'اتصال به گوگل برقرار نشد ({type(e).__name__}) — اگر سرور در ایران است پراکسی لازم است') from e
        if r.status_code != 200:
            raise GSCError(f'گرفتنِ توکن ناموفق ({r.status_code}): {r.text[:300]}')
        tok = r.json()['access_token']
        cache.set(key, tok, 3000)
        return tok

    def _req(self, method, path, body=None):
        try:
            r = self.s.request(method, API + path, json=body, timeout=90, headers={'Authorization': 'Bearer ' + self._token()})
        except requests.RequestException as e:
            raise GSCError(f'اتصال به API سرچ کنسول برقرار نشد ({type(e).__name__})') from e
        if r.status_code >= 400:
            try:
                msg = r.json().get('error', {}).get('message', '')
            except ValueError:
                msg = r.text[:300]
            raise GSCError(f'خطای سرچ کنسول ({r.status_code}): {msg}')
        return r.json() if r.content else {}

    def sites(self):
        return self._req('GET', '/sites').get('siteEntry', [])

    def query(self, site_url, start, end, dimensions, row_limit=25000, max_rows=500000):
        """همهٔ ردیف‌ها با صفحه‌بندی (startRow). تاریخ‌ها date."""
        out, start_row = [], 0
        while True:
            body = {'startDate': start.isoformat(), 'endDate': end.isoformat(), 'dimensions': dimensions,
                    'rowLimit': row_limit, 'startRow': start_row, 'type': 'web', 'dataState': 'final'}
            rows = self._req('POST', f'/sites/{quote(site_url, safe="")}/searchAnalytics/query', body).get('rows', [])
            out.extend(rows)
            if len(rows) < row_limit or len(out) >= max_rows:
                return out
            start_row += row_limit
