"""API‌های JSON بستهٔ سئو — بدون DRF. دو دسته:
۱) مدیریتِ کلمات/صفحاتِ ردیابی‌شده (از تبِ «کلمات کلیدی» پروژه، سشنِ کاربرِ لاگین‌شده).
۲) دریافتِ داده از **افزونهٔ مرورگر** (`rank_ingest`, `tracked_domains`) — با
   **توکنِ API** (`Authorization: Token xxx`، از `/settings/api-tokens/`)، نه سشن؛
   چون افزونه از یک fetchِ کراس‌سایت (google.com ← این پلتفرم) صدا می‌زند و
   SameSite=Lax کوکیِ سشن را در چنین درخواستی نمی‌فرستد. `token_or_login_required`
   هردو راه را قبول می‌کند تا تست از خودِ مرورگرِ اپ هم کار کند.
"""
import json
from datetime import date
from functools import wraps
from urllib.parse import urlparse

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.models import APIToken
from accounts.tenancy import set_current_org
from projects.models import Project

from .models import KeywordRankSnapshot, TrackedKeyword


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}


def _authenticate_token(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Token '):
        return None
    token = APIToken.authenticate(auth[len('Token '):].strip())
    if token:
        set_current_org(token.organization)
        request.user = token.user
        token.touch()
    return token


def token_or_login_required(view):
    """برای ویوهای فقط‌خواندنی: `Authorization: Token xxx` (افزونه) یا سشنِ عادی
    (کاربرِ لاگین‌شده در خودِ اپ، برای تست/دیباگ). GET بودن یعنی مسیرِ سشن نیازی به
    بررسیِ CSRF ندارد."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if _authenticate_token(request):
            return view(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return JsonResponse({'detail': 'ورود یا توکنِ API لازم است'}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def token_required(view):
    """برای ویوهایی که داده می‌نویسند و افزونه صداشان می‌زند: **فقط توکن**، بدونِ
    مسیرِ جایگزینِ سشن. این‌طور نیازی به معاف‌کردنِ CSRF نیست — توکن اصلاً کوکیِ سشن
    نیست که CSRF رویش معنا داشته باشد (مثلِ همه‌ی auth‌های Bearer-token)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not _authenticate_token(request):
            return JsonResponse({'detail': 'توکنِ API نامعتبر یا غایب است'}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def _normalize_host(value):
    """میزبان را برای مقایسه یکدست می‌کند: بدون www.، حروفِ کوچک."""
    host = (value or '').strip().lower()
    if '//' in host:
        host = urlparse(host).hostname or ''
    host = host.split('/')[0].split(':')[0]
    return host[4:] if host.startswith('www.') else host


# ── مدیریتِ کلمات/صفحات (تبِ کلمات‌کلیدیِ پروژه) ──────────────────────────

@login_required
@require_http_methods(['POST'])
def keyword_add(request):
    """افزودنِ «صفحهٔ مهم» + چند کلمهٔ کلیدی با آن، به‌صورتِ دستی (ستاره‌دار).
    بدنه: {project, page_url, keywords: [str, ...]}"""
    data = _body(request)
    project = get_object_or_404(Project, pk=data.get('project'))
    page_url = (data.get('page_url') or '').strip()
    keywords = [k.strip() for k in (data.get('keywords') or []) if k and k.strip()]
    if not page_url or not keywords:
        return JsonResponse({'detail': 'لینک صفحه و حداقل یک کلمه کلیدی لازم است'}, status=400)
    created = []
    for kw in keywords:
        tk, _ = TrackedKeyword.objects.update_or_create(
            project=project, page_url=page_url, keyword=kw,
            defaults={'is_manual': True, 'is_starred': True})
        created.append(tk.id)
    return JsonResponse({'ok': True, 'ids': created}, status=201)


@login_required
@require_http_methods(['PATCH', 'DELETE'])
def keyword_edit(request, pk):
    tk = get_object_or_404(TrackedKeyword, pk=pk)
    if request.method == 'DELETE':
        tk.delete()
        return JsonResponse({'ok': True})
    data = _body(request)
    if 'keyword' in data:
        tk.keyword = (data['keyword'] or '').strip() or tk.keyword
    if 'page_url' in data:
        tk.page_url = (data['page_url'] or '').strip() or tk.page_url
    if 'is_starred' in data:
        tk.is_starred = bool(data['is_starred'])
    tk.save()
    return JsonResponse({'ok': True, 'id': tk.id, 'is_starred': tk.is_starred})


@login_required
@require_http_methods(['PATCH'])
def page_rename(request):
    """تغییرِ نامِ یک «صفحه» = تغییرِ `page_url` روی همهٔ کلماتِ زیرِ آن، یک‌جا.
    بدنه: {project, old_url, new_url}"""
    data = _body(request)
    project = get_object_or_404(Project, pk=data.get('project'))
    old_url, new_url = (data.get('old_url') or '').strip(), (data.get('new_url') or '').strip()
    if not old_url or not new_url:
        return JsonResponse({'detail': 'لینکِ قدیم و جدید لازم است'}, status=400)
    n = TrackedKeyword.objects.filter(project=project, page_url=old_url).update(page_url=new_url)
    return JsonResponse({'ok': True, 'updated': n})


@login_required
@require_http_methods(['PATCH'])
def page_star(request):
    """ستاره‌دار/بی‌ستاره‌کردنِ یک «صفحه» = روی همهٔ کلماتِ زیرِ آن یک‌جا.
    بدنه: {project, page_url, is_starred}"""
    data = _body(request)
    project = get_object_or_404(Project, pk=data.get('project'))
    page_url = (data.get('page_url') or '').strip()
    n = TrackedKeyword.objects.filter(project=project, page_url=page_url).update(
        is_starred=bool(data.get('is_starred')))
    return JsonResponse({'ok': True, 'updated': n})


@login_required
@require_http_methods(['GET', 'POST'])
def keyword_history(request, pk):
    """تاریخچهٔ روزانهٔ یک کلمه (۹۰ روزِ اخیر) + امکانِ ثبتِ/اصلاحِ دستیِ یک روز.
    POST بدنه: {date: 'YYYY-MM-DD', position: int}"""
    tk = get_object_or_404(TrackedKeyword, pk=pk)
    if request.method == 'POST':
        data = _body(request)
        try:
            d = date.fromisoformat(data.get('date', ''))
            pos = int(data.get('position'))
        except (ValueError, TypeError):
            return JsonResponse({'detail': 'تاریخ/جایگاهِ نامعتبر'}, status=400)
        if pos < 1:
            return JsonResponse({'detail': 'جایگاه باید حداقل ۱ باشد'}, status=400)
        snap, _ = KeywordRankSnapshot.objects.update_or_create(
            keyword=tk, date=d, defaults={'position': pos})
        return JsonResponse({'ok': True, 'date': str(snap.date), 'position': snap.position})
    snaps = tk.snapshots.order_by('-date')[:90]
    return JsonResponse({'snapshots': [{'date': str(s.date), 'position': s.position} for s in snaps]})


# ── ورودیِ داده از افزونهٔ مرورگر ──────────────────────────────────────────

@token_or_login_required
@require_http_methods(['GET'])
def tracked_domains(request):
    """دامنه‌هایی که افزونه باید در نتایجِ گوگل زیر نظر بگیرد (پروژه‌های همین سازمان
    با تیکِ «بررسی رتبه کلمات کلیدی»)."""
    projects = Project.objects.filter(track_keyword_rank=True).exclude(domain='')
    return JsonResponse({
        'domains': [{'project': p.id, 'domain': _normalize_host(p.domain)} for p in projects],
    })


@csrf_exempt
@token_required
@require_http_methods(['POST'])
def rank_ingest(request):
    """ثبتِ یک مشاهدهٔ افزونه از نتایجِ گوگل. بدنه: {url, keyword, position, date?}.
    اگر دامنهٔ `url` به هیچ پروژهٔ ردیابی‌شده‌ای نخورد، بی‌سروصدا نادیده گرفته می‌شود
    (افزونه در هر سرچی این را صدا می‌زند، نه فقط برای سایت‌های ما).
    در یک روز فقط یک رکورد برای هر کلمه می‌ماند — سرچِ جدیدترِ همان روز جایگزین می‌شود."""
    data = _body(request)
    url = (data.get('url') or '').strip()
    keyword = (data.get('keyword') or '').strip()
    try:
        position = int(data.get('position'))
    except (TypeError, ValueError):
        return JsonResponse({'detail': 'جایگاهِ نامعتبر'}, status=400)
    if not url or not keyword or position < 1:
        return JsonResponse({'detail': 'url، keyword و position لازم است'}, status=400)
    try:
        d = date.fromisoformat(data['date']) if data.get('date') else date.today()
    except (ValueError, TypeError):
        d = date.today()

    host = _normalize_host(url)
    project = next(
        (p for p in Project.objects.filter(track_keyword_rank=True).exclude(domain='')
         if host == _normalize_host(p.domain) or host.endswith('.' + _normalize_host(p.domain))),
        None)
    if not project:
        return JsonResponse({'matched': False})

    tk, _ = TrackedKeyword.objects.get_or_create(
        project=project, page_url=url, keyword=keyword,
        defaults={'is_manual': False, 'is_starred': False})
    KeywordRankSnapshot.objects.update_or_create(
        keyword=tk, date=d, defaults={'position': position, 'seen_url': url})
    return JsonResponse({'matched': True, 'project': project.id, 'keyword_id': tk.id})
