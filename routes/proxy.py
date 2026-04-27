'\n代理路由：GET/POST /api/proxy，转发请求并重写 HTML 链接。\n子资源代理：当 Referer 来自代理页时，将 /sugrec、/widget 等相对路径请求转发到目标站点。\n'
_O='unsafe-url'
_N='Referrer-Policy'
_M='Content-Type'
_L='referer'
_K='url'
_J='Referer'
_I=True
_H='POST'
_G='Accept'
_F='text/html'
_E='/api/proxy'
_D='https://'
_C='http://'
_B='text/plain'
_A='/'
import re
from urllib.parse import parse_qs,quote,urlencode,urljoin,urlparse
import requests
from fastapi import APIRouter,Query,Request
from fastapi.responses import Response
router=APIRouter(tags=['proxy'])
PROXY_TIMEOUT=20
PROXY_HEADERS={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',_G:'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8','Accept-Language':'zh-CN,zh;q=0.9,en;q=0.8','Sec-Fetch-Mode':'navigate','Sec-Fetch-Site':'none'}
def _headers_for_url(url:str,referer:str,content_type_hint:str=''):
	'根据目标 URL 与内容类型返回合适的请求头。';G='image';E=referer;D='Sec-Fetch-Dest';B=content_type_hint;A=dict(PROXY_HEADERS);A[_J]=E
	try:F=urlparse(E);H=f"{F.scheme}://{F.netloc}";A['Origin']=H
	except Exception:pass
	C=(url or'').lower()
	if'.css'in C or'text/css'in B:A[_G]='text/css,*/*;q=0.1';A[D]='style'
	elif'.js'in C or'javascript'in B:A[_G]='*/*';A[D]='script'
	elif G in B or any(A in C for A in('.png','.jpg','.jpeg','.gif','.webp','.svg','.ico')):A[_G]='image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8';A[D]=G
	return A
def _rewrite_html_links(html:bytes,base_url:str,proxy_base:str):
	'\n    重写 HTML：1) 注入 <base href="..."> 使相对路径请求到目标站；2) 重写链接与 form action 经代理。\n    ';K='<meta name="referrer" content="unsafe-url">';J='<base';I='<head>';H='javascript:';G='replace';F='utf-8';C=proxy_base;B=base_url
	try:A=html.decode(F,errors=G)
	except Exception:return html
	D=urlparse(B);L=f"{D.scheme}://{D.netloc}/"
	def M(m:re.Match):
		A=m.group(2)
		if not A or A.startswith('#')or A.startswith(H)or A.startswith('mailto:')or A.startswith('data:'):return m.group(0)
		try:
			D=urljoin(B,A)
			if D.startswith(_C)or D.startswith(_D):E=quote(D,safe='');return f'href="{C}?url={E}"'
		except Exception:pass
		return m.group(0)
	def N(m:re.Match):
		A=m.group(2)
		if not A or A.startswith(H)or A.startswith('#'):return m.group(0)
		try:
			D=urljoin(B,A)
			if D.startswith(_C)or D.startswith(_D):E=quote(D,safe='');return f'action="{C}?url={E}"'
		except Exception:pass
		return m.group(0)
	E=f'<base href="{L}">'
	if I in A.lower()and J not in A.lower():A=re.sub('<head[^>]*>',lambda m:m.group(0)+E,A,count=1,flags=re.I)
	elif'<html'in A.lower()and J not in A.lower():A=re.sub('<html[^>]*>',lambda m:m.group(0)+I+E+'</head>',A,count=1,flags=re.I)
	A=re.sub('<meta\\s+name\\s*=\\s*["\\\']?referrer["\\\']?[^>]*content\\s*=\\s*["\\\']?no-referrer["\\\']?[^>]*>',K,A,flags=re.I);A=re.sub('<meta\\s+content\\s*=\\s*["\\\']?no-referrer["\\\']?[^>]*name\\s*=\\s*["\\\']?referrer["\\\']?[^>]*>',K,A,flags=re.I);A=re.sub('\\bhref=(["\\\'])([^"\\\']*)\\1',M,A);A=re.sub('\\baction=(["\\\'])([^"\\\']*)\\1',N,A);A=re.sub('\\btarget=(["\\\'])\\s*_blank\\s*\\1','target=\\1_self\\1',A,flags=re.I)
	def O(m:re.Match):
		D,E,F=m.group(1),m.group(2),m.group(3)
		try:
			A=urljoin(B,E)
			if A.startswith(_C)or A.startswith(_D):G=quote(A,safe='');return f"{D}{C}?url={G}{F}"
		except Exception:pass
		return m.group(0)
	A=re.sub('(content\\s*=\\s*["\\\']\\d+\\s*;\\s*url\\s*=\\s*)([^\\s;"\\\']+)(["\\\']\\s*[^>]*>)',O,A,flags=re.I);return A.encode(F,errors=G)
def _get_target_from_referer(request:Request):
	'\n    当请求缺少 url 参数时（如表单 action="?" 提交导致 query 被 form 字段覆盖），\n    从 Referer 提取 base URL，与当前 query 拼接成目标地址。\n    ';D=request;E=D.headers.get(_L)or D.headers.get(_J)or''
	if _E not in E or'url='not in E:return
	try:
		G=urlparse(E);I=parse_qs(G.query)if G.query else{};B=I.get(_K)
		if not B:return
		F=B[0]if isinstance(B,list)else str(B)
		if not F.startswith(_C)and not F.startswith(_D):return
		A=urlparse(F);C=f"{A.scheme}://{A.netloc}{A.path or _A}".rstrip(_A)or f"{A.scheme}://{A.netloc}/"
		if not C.endswith(_A):C+=_A
		H=D.url.query;return f"{C.rstrip(_A)}?{H}"if H else C.rstrip(_A)
	except Exception:return
@router.api_route(_E,methods=['GET',_H])
async def proxy_url(request:Request,url:str|None=Query(None,description='要由后端代为请求的 http(s) 地址')):
	'\n    后端代理请求：前端将 iframe.src 设为本接口，由服务端请求目标 URL 并返回内容。\n    若返回 HTML，会重写链接与表单 action，使点击/提交继续经代理转发并重新渲染。\n    当 url 缺失时（如表单 action="?" 提交），从 Referer 推断目标地址。\n    ';C=request;A=url
	if not A or not(A.startswith(_C)or A.startswith(_D)):A=_get_target_from_referer(C)
	if not A or not(A.startswith(_C)or A.startswith(_D)):return Response(content='仅支持 http:// 或 https:// 链接，且需提供 url 参数或来自代理页的 Referer',status_code=400,media_type=_B)
	try:
		F=_headers_for_url(A,A)
		if C.method==_H:I=await C.form();J={A:B for(A,B)in I.items()};B=requests.post(A,data=J,timeout=PROXY_TIMEOUT,headers=F,allow_redirects=_I)
		else:
			G={A:B for(A,B)in C.query_params.items()if A!=_K};H=A
			if G:K='&'if'?'in A else'?';H=A+K+urlencode(G)
			B=requests.get(H,timeout=PROXY_TIMEOUT,headers=F,allow_redirects=_I)
		B.raise_for_status();D=B.headers.get(_M,'text/html; charset=utf-8').split(';')[0].strip().lower();E=B.content
		if _F in D:L=_E;E=_rewrite_html_links(E,B.url,L)
		M={_N:_O}if _F in D else{};return Response(content=E,media_type=D or _F,headers=M)
	except requests.RequestException as N:return Response(content=f"代理请求失败: {N!s}",status_code=502,media_type=_B)
@router.api_route('/{sub_path:path}',methods=['GET',_H])
async def proxy_sub_request(request:Request,sub_path:str):
	'\n    子资源代理：当 Referer 来自 /api/proxy?url=... 时，将相对路径请求（如 /sugrec、/widget）\n    转发到目标站点，解决页面内 XHR/fetch 因同源策略导致的 404。\n    ';E=sub_path;C=request;G=C.headers.get(_L)or C.headers.get(_J)or''
	if _E not in G or'url='not in G:return Response(content='Not Found',status_code=404,media_type=_B)
	try:
		J=urlparse(G);M=parse_qs(J.query)if J.query else{};F=M.get(_K)
		if not F:return Response(content='Missing url in Referer',status_code=400,media_type=_B)
		B=F[0]if isinstance(F,list)else str(F)
	except Exception:return Response(content='Invalid Referer',status_code=400,media_type=_B)
	N=urlparse(B)
	if not N.netloc:return Response(content='Invalid base URL',status_code=400,media_type=_B)
	if not B.endswith(_A):B=B.rstrip(_A)+_A
	if E.startswith('api/api/'):E=E[4:]
	A=urljoin(B,_A+E);K=C.url.query
	if K:A=A+('&'if'?'in A else'?')+K
	if not A.startswith(_C)and not A.startswith(_D):return Response(content='Invalid target',status_code=400,media_type=_B)
	try:
		L=_headers_for_url(A,B)
		if C.method==_H:O=await C.form();P={A:B for(A,B)in O.items()};D=requests.post(A,data=P,timeout=PROXY_TIMEOUT,headers=L,allow_redirects=_I)
		else:D=requests.get(A,timeout=PROXY_TIMEOUT,headers=L,allow_redirects=_I)
		D.raise_for_status();H=D.headers.get(_M,'').split(';')[0].strip().lower();I=D.content
		if _F in H:Q=_E;I=_rewrite_html_links(I,D.url,Q)
		R={_N:_O}if _F in H else{};return Response(content=I,media_type=H or'application/octet-stream',headers=R)
	except requests.RequestException as S:return Response(content=f"代理请求失败: {S!s}",status_code=502,media_type=_B)