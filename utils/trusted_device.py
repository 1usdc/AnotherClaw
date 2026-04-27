'\nUser-Agent + 设备指纹：可选启用时拦截未登记的 API / WebSocket / 代理子路径；\n管理接口仅允许本机或通过 ``DEVICE_AUTH_ADMIN_TOKEN`` 头访问（便于 SSH 后 curl）。\n'
from __future__ import annotations
_D='user-agent'
_C=False
_B='GET'
_A=True
import os
from fastapi import WebSocket
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp,Receive,Scope,Send
from utils.db import db_trusted_device_count,db_trusted_device_pair_exists
HEADER_DEVICE_FINGERPRINT='x-device-fingerprint'
HEADER_ADMIN_TOKEN='x-device-auth-admin-token'
_ENV_ENABLED='DEVICE_AUTH_ENABLED'
_ENV_ADMIN_TOKEN='DEVICE_AUTH_ADMIN_TOKEN'
_ENV_ALLOW_EMPTY='DEVICE_AUTH_ALLOW_EMPTY'
_SPA_GET_EXEMPT=frozenset({'/','/home','/learn','/skill','/memory'})
def device_auth_is_enabled():'是否启用 UA + 设备指纹校验（环境变量 ``DEVICE_AUTH_ENABLED`` 为 1/true/yes/on）。';A=(os.environ.get(_ENV_ENABLED)or'').strip().lower();return A in('1','true','yes','on')
def device_auth_allow_empty_allowlist():'库中无任何登记时是否放行所有设备（默认否）。';A=(os.environ.get(_ENV_ALLOW_EMPTY)or'').strip().lower();return A in('1','true','yes','on')
def _normalize_ua(ua:str):A=(ua or'').strip();return A[:4096]
def _normalize_fp(fp:str):A=(fp or'').strip();return A[:2048]
def extract_ua_fp_from_http_scope(scope:Scope):'从 ASGI HTTP scope 解析 User-Agent 与 ``X-Device-Fingerprint``。';B='latin-1';A={A.decode(B).lower():C.decode(B,'replace')for(A,C)in scope.get('headers')or[]};C=_normalize_ua(A.get(_D,''));D=_normalize_fp(A.get(HEADER_DEVICE_FINGERPRINT,''));return C,D
def is_path_exempt_from_device_auth(path:str,method:str):
	'\n    无需设备认证的路径：静态资源、SPA 入口 HTML、内置头像文件、管理接口。\n\n    :param path: 请求路径\n    :param method: HTTP 方法；WebSocket 校验时传入 ``GET``\n    ';A=path;A=A or'/';B=(method or _B).upper()
	if B=='OPTIONS':return _A
	if A.startswith('/assets/')or A=='/favicon.ico':return _A
	if A.startswith('/internal/trusted-devices'):return _A
	if A in _SPA_GET_EXEMPT and B in(_B,'HEAD'):return _A
	if B==_B and(A.startswith('/api/avators/')or A.startswith('/api/avatar/')or A.startswith('/static/assets/avators/')or A.startswith('/static/assets/avatar/')):return _A
	if A in('/docs','/redoc','/openapi.json'):return _A
	return _C
def requires_device_auth_check(path:str,method:str):
	'当前请求是否需要 UA + 指纹（在已启用设备认证前提下）。'
	if is_path_exempt_from_device_auth(path,method):return _C
	return _A
async def verify_websocket_trusted_device(websocket:WebSocket):
	'\n    WebSocket 握手前校验：指纹在查询参数 ``device_fingerprint``；\n    User-Agent 使用握手请求头 ``user-agent``（与 HTTP 一致）。\n\n    :returns: 是否可继续 ``accept()``；若返回 False，已尝试关闭连接。\n    ';A=websocket
	if not device_auth_is_enabled():return _A
	B=A.url.path
	if is_path_exempt_from_device_auth(B,_B):return _A
	if db_trusted_device_count()==0 and device_auth_allow_empty_allowlist():return _A
	C=_normalize_ua(A.headers.get(_D,''));D=_normalize_fp((A.query_params.get('device_fingerprint')or'').strip())
	if is_trusted_pair(C,D):return _A
	await A.close(code=1008,reason='device_not_trusted');return _C
def is_trusted_pair(user_agent:str,fingerprint:str):
	'查询数据库是否登记了该 UA + 指纹对。';A=fingerprint
	if not _normalize_fp(A):return _C
	return db_trusted_device_pair_exists(_normalize_ua(user_agent),_normalize_fp(A))
class TrustedDeviceAuthMiddleware:
	'\n    ASGI 中间件：对 HTTP 在启用时校验 ``User-Agent`` + ``X-Device-Fingerprint``。\n    WebSocket 在路由内单独校验（见 ``verify_websocket_trusted_device``）。\n    '
	def __init__(A,app:ASGIApp):A.app=app
	async def __call__(D,scope:Scope,receive:Receive,send:Send):
		C=send;B=receive;A=scope
		if A.get('type')!='http':await D.app(A,B,C);return
		if not device_auth_is_enabled():await D.app(A,B,C);return
		E=A.get('path')or'/';F=A.get('method',_B)
		if not requires_device_auth_check(E,F):await D.app(A,B,C);return
		G,H=extract_ua_fp_from_http_scope(A)
		if db_trusted_device_count()==0 and device_auth_allow_empty_allowlist():await D.app(A,B,C);return
		if is_trusted_pair(G,H):await D.app(A,B,C);return
		I=JSONResponse(status_code=403,content={'detail':'设备未授权：请在服务端登记与当前请求一致的 User-Agent 与 X-Device-Fingerprint（WebSocket 使用请求头 UA + 查询参数 device_fingerprint）。','hint':'管理接口：GET/POST/DELETE /internal/trusted-devices（仅本机或 X-Device-Auth-Admin-Token）'});await I(A,B,C)
def admin_request_authorized(request:Request):
	'\n    管理接口是否允许访问：来源为回环地址，或请求头 ``X-Device-Auth-Admin-Token`` 与环境变量一致。\n    ';A=request;C=A.client.host if A.client else''
	if C in('127.0.0.1','::1','localhost'):return _A
	B=(os.environ.get(_ENV_ADMIN_TOKEN)or'').strip()
	if not B:return _C
	D=(A.headers.get(HEADER_ADMIN_TOKEN)or'').strip();return D==B