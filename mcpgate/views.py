"""endpointِ MCP (Streamable HTTP، بی‌حالت) + صفحهٔ `/settings/mcp/` و APIِ مدیریتِ سایت‌ها."""
import json
import time

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.access import require_perm

from . import tools as T
from . import wp
from .models import MCPGate, MCPLog, MCPSite, new_token

PERM = 'manage_api_tokens'
VERSIONS = ('2025-06-18', '2025-03-26', '2024-11-05')


def _cors(resp):
    resp['Access-Control-Allow-Origin'] = '*'
    resp['Access-Control-Allow-Headers'] = '*'
    resp['Access-Control-Allow-Methods'] = 'POST, GET, DELETE, OPTIONS'
    resp['Access-Control-Expose-Headers'] = 'Mcp-Session-Id'
    return resp


def _gate_from(request, token):
    if not token:
        auth = request.headers.get('Authorization', '')
        token = auth.split(' ', 1)[1].strip() if ' ' in auth else ''
    return MCPGate.objects.filter(token=token, enabled=True).select_related('organization').first() if token else None


def _server(kind):
    """kind: site (ابزارهای سایت‌ها، `tools.py`) | panel (`panel/registry.py`) | skills (`skills/mcp.py`)."""
    from skills import mcp as SK

    from .panel import registry as PR
    if kind == 'panel':
        return PR.TOOLS, PR.INSTRUCTIONS, PR.run, 'seo-manager-panel'
    if kind == 'skills':
        return SK.TOOLS, None, SK.run, 'seo-manager-skills'
    return T.TOOLS, T.INSTRUCTIONS, (lambda gate, name, args, log: T.run(gate.organization, name, args, log)), 'seo-manager'


def _instructions(gate, kind, base):
    """متنِ اسکیل‌های «اجباری» (must use) در instructionsِ هر سه کانکتور — تا در هر گفتگو رعایت شود."""
    from skills import mcp as SK
    from skills.text import must_use_text
    if kind == 'skills':
        return SK.instructions(gate.organization)
    from skills.text import live
    must = must_use_text(gate.organization)
    if live(gate.organization).exists():
        must = ('قبل از تولید/ویرایشِ محتوا، از کانکتورِ «اسکیل‌ها» skills_start(text=درخواستِ کاربر، site/project) را بزن '
                'و اسکیل‌های load را رعایت کن.' + ('\n\n' + must if must else ''))
    return base + ('\n\n' + must if must else '')


def _handle(gate, msg, kind='site'):
    from .panel.ctx import ToolError as PanelError
    mid, method, params = msg.get('id'), msg.get('method'), msg.get('params') or {}
    tools_list, base_instructions, runner, server_name = _server(kind)
    ok = lambda result: {'jsonrpc': '2.0', 'id': mid, 'result': result}  # noqa: E731
    if method == 'initialize':
        v = params.get('protocolVersion')
        return ok({'protocolVersion': v if v in VERSIONS else VERSIONS[0], 'capabilities': {'tools': {'listChanged': False}},
                   'serverInfo': {'name': server_name, 'version': '1.2.0'},
                   'instructions': _instructions(gate, kind, base_instructions)})
    if method == 'ping':
        return ok({})
    if method == 'tools/list':
        return ok({'tools': tools_list})
    if method in ('resources/list', 'prompts/list', 'resources/templates/list'):
        key = {'resources/list': 'resources', 'prompts/list': 'prompts'}.get(method, 'resourceTemplates')
        return ok({key: []})
    if method == 'tools/call':
        name, args = params.get('name'), params.get('arguments') or {}
        log, t0 = {}, time.monotonic()
        try:
            res = runner(gate, name, args, log)
            out = T.to_content(res)
            err = ''
        except (T.ToolError, PanelError, wp.WPError, KeyError, ValueError, TypeError) as e:
            err = f'{type(e).__name__}: {e}' if isinstance(e, (KeyError, TypeError)) else str(e)
            out = {'content': [{'type': 'text', 'text': f'خطا: {err}'}], 'isError': True}
        except Exception as e:  # noqa: BLE001 — هیچ خطایی نباید endpoint را بخواباند
            err = f'{type(e).__name__}: {e}'
            out = {'content': [{'type': 'text', 'text': f'خطای داخلی: {err}'}], 'isError': True}
        if kind != 'site' and not log.get('summary'):
            log['summary'] = json.dumps({k: (v if not isinstance(v, list) else f'[{len(v)}]') for k, v in (args or {}).items()},
                                        ensure_ascii=False, default=str)[:300]
        MCPLog.objects.create(organization=gate.organization, site=log.get('site', ''), tool=str(name)[:80],
                              summary=log.get('summary', '')[:300], ok=not err, error=err[:2000],
                              ms=int((time.monotonic() - t0) * 1000), backup=log.get('backup'))
        return ok(out)
    if mid is None:  # notification
        return None
    return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': f'Method not found: {method}'}}


@csrf_exempt
def endpoint_panel(request, token=''):
    return endpoint(request, token, kind='panel')


@csrf_exempt
def endpoint_skills(request, token=''):
    return endpoint(request, token, kind='skills')


@csrf_exempt
def endpoint(request, token='', kind='site'):
    if request.method == 'OPTIONS':
        return _cors(HttpResponse(status=204))
    gate = _gate_from(request, token)
    if not gate:
        return _cors(JsonResponse({'error': 'توکنِ MCP نامعتبر یا غیرفعال است'}, status=401))
    if request.method == 'GET':
        return _cors(HttpResponse(status=405))  # استریمِ SSE نداریم (بی‌حالت)
    if request.method == 'DELETE':
        return _cors(HttpResponse(status=200))
    if request.method != 'POST':
        return _cors(HttpResponse(status=405))
    try:
        msg = json.loads(request.body or b'null')
    except ValueError:
        return _cors(JsonResponse({'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Parse error'}}, status=400))
    gate._base = request.build_absolute_uri('/')
    batch = isinstance(msg, list)
    replies = [r for r in (_handle(gate, m, kind) for m in (msg if batch else [msg]) if isinstance(m, dict)) if r is not None]
    if not replies:
        return _cors(HttpResponse(status=202))
    resp = JsonResponse(replies if batch else replies[0], safe=False, json_dumps_params={'ensure_ascii': False})
    return _cors(resp)


# ───────────── صفحهٔ تنظیمات ─────────────
def _gate(org, user=None):
    gate, _ = MCPGate.objects.get_or_create(organization=org)
    if user is not None and gate.user_id is None:
        gate.user = user          # کارهای MCPِ پنل به نامِ همین کاربر ثبت می‌شود
        gate.save(update_fields=['user'])
    return gate


def import_from_sync(org):
    """سایت‌های برنامهٔ ویندوزیِ ChatGPT-WP (انبارِ همگام‌سازیِ `connector`) → MCPSite. بر اساسِ key ادغام می‌شود."""
    from connector.models import SyncStore
    store = SyncStore.objects.filter(organization=org).first()
    sites = (store.get_data() if store else {}).get('sites') or []
    added = updated = 0
    for s in sites:
        key = (s.get('key') or '').strip()
        if not key or not s.get('url'):
            continue
        obj, created = MCPSite.objects.get_or_create(organization=org, key=key, defaults={'url': s['url']})
        obj.url = s['url']
        obj.wp_user = (s.get('user') or obj.wp_user or '').strip()
        if s.get('password'):
            obj.password = s['password'].strip()
        obj.notes = obj.notes or s.get('notes') or ''
        obj.active = s.get('active', True) is not False
        obj.save()
        added += created
        updated += not created
    return added, updated


@login_required
def page(request):
    org = require_perm(request, PERM)
    gate = _gate(org, request.user)
    from connector.models import SyncStore
    store = SyncStore.objects.filter(organization=org).first()
    sync_sites = len((store.get_data() if store else {}).get('sites') or [])
    if sync_sites and not MCPSite.objects.filter(organization=org).exists():
        import_from_sync(org)  # بارِ اول: دادهٔ برنامهٔ ویندوزی خودکار بیاید
    return render(request, 'mcpgate/page.html', {
        'page_title': 'اتصالِ MCP',
        'gate': gate,
        'mcp_url': request.build_absolute_uri(f'/mcp/{gate.token}/'),
        'mcp_panel_url': request.build_absolute_uri(f'/mcp/{gate.token}/panel/'),
        'mcp_skills_url': request.build_absolute_uri(f'/mcp/{gate.token}/skills/'),
        'sites': [s.brief() for s in MCPSite.objects.filter(organization=org)],
        'logs': MCPLog.objects.filter(organization=org)[:40],
        'sync_sites': sync_sites,
    })


def _body(request):
    try:
        return json.loads(request.body or b'{}')
    except ValueError:
        return {}


@login_required
@require_http_methods(['POST'])
def gate_update(request):
    org = require_perm(request, PERM)
    gate = _gate(org)
    d = _body(request)
    if d.get('regenerate'):
        gate.token = new_token()
    if 'enabled' in d:
        gate.enabled = bool(d['enabled'])
    gate.save()
    return JsonResponse({'url': request.build_absolute_uri(f'/mcp/{gate.token}/'), 'enabled': gate.enabled})


@login_required
@require_http_methods(['POST'])
def site_save(request):
    org = require_perm(request, PERM)
    d = _body(request)
    key, url = (d.get('key') or '').strip(), (d.get('url') or '').strip().rstrip('/')
    if not key or not url:
        return JsonResponse({'detail': 'نامِ کوتاه و آدرس لازم است'}, status=400)
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    site = get_object_or_404(MCPSite, pk=d['id'], organization=org) if d.get('id') else MCPSite(organization=org)
    if MCPSite.objects.filter(organization=org, key=key).exclude(pk=site.pk).exists():
        return JsonResponse({'detail': 'این نامِ کوتاه تکراری است'}, status=400)
    site.key, site.url = key, url
    site.wp_user = (d.get('user') or '').strip()
    if d.get('password'):
        site.password = d['password'].strip()
    site.mcp_path = (d.get('mcp_path') or 'mcp/novamira').strip().strip('/')
    site.notes = d.get('notes') or ''
    site.active = d.get('active', True) is not False
    site.save()
    from django.core.cache import cache
    cache.delete_many([f'mcpgate:mcpsess:{site.pk}', f'mcpgate:disc:{site.pk}', f'mcpgate:restroute:{site.pk}'])
    return JsonResponse({'site': site.brief()})


@login_required
@require_http_methods(['POST'])
def site_delete(request, pk):
    org = require_perm(request, PERM)
    get_object_or_404(MCPSite, pk=pk, organization=org).delete()
    return JsonResponse({'ok': True})


@login_required
@require_http_methods(['POST'])
def site_test(request, pk):
    org = require_perm(request, PERM)
    site = get_object_or_404(MCPSite, pk=pk, organization=org)
    from django.core.cache import cache
    cache.delete_many([f'mcpgate:mcpsess:{site.pk}', f'mcpgate:disc:{site.pk}'])
    res = T.check(site)
    site.last_check = {'ok': res['ok'], 'novamira': res['novamira']['ok'], 'at': int(time.time()),
                       'error': res['rest'].get('error') or '', 'novamira_error': res['novamira'].get('error') or ''}
    site.save(update_fields=['last_check'])
    return JsonResponse({'result': res, 'site': site.brief()})


@login_required
@require_http_methods(['POST'])
def site_import(request):
    org = require_perm(request, PERM)
    added, updated = import_from_sync(org)
    return JsonResponse({'added': added, 'updated': updated,
                         'sites': [s.brief() for s in MCPSite.objects.filter(organization=org)]})


# ───────────── لاگ و بازگردانیِ تغییراتِ MCPِ پنل ─────────────
@login_required
def log_page(request, pk=None):
    from django.core.paginator import Paginator

    from .models import MCPBatch
    org = require_perm(request, PERM)
    qs = MCPBatch.objects.filter(organization=org).select_related('user', 'undone_by')
    if request.GET.get('tool'):
        qs = qs.filter(tool=request.GET['tool'])
    page = Paginator(qs, 40).get_page(request.GET.get('page'))
    current = qs.filter(pk=pk).first() if pk else None
    changes = list(current.changes.all()[:500]) if current else []
    return render(request, 'mcpgate/log.html', {'page_title': 'لاگِ MCP', 'page_obj': page, 'batches': page.object_list,
                                                'current': current, 'changes': changes})


@login_required
@require_http_methods(['POST'])
def log_undo(request, pk):
    from . import journal
    from .models import MCPBatch
    org = require_perm(request, PERM)
    b = get_object_or_404(MCPBatch, pk=pk, organization=org)
    res = journal.undo(b, request.user, force=bool(_body(request).get('force')))
    return JsonResponse(res)
