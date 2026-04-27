'\nHTTP 请求工具：用 Python 请求 URL，优先使用 requests（SSL 兼容性更好）。\n'
_C='replace'
_B='AnotherMe/1.0'
_A='User-Agent'
import ssl,urllib.request
from typing import Annotated
from langchain_core.tools import tool
FETCH_TIMEOUT=15
def _fetch_with_requests(url:str):'使用 requests 请求，SSL 行为更稳定。';import requests as B;A=B.get(url,timeout=FETCH_TIMEOUT,headers={_A:_B});A.raise_for_status();return A.text
def _fetch_with_urllib(url:str):
	'备用：urllib + 显式 TLS 1.2，缓解部分 UNEXPECTED_EOF_WHILE_READING。';A=ssl.create_default_context();A.minimum_version=ssl.TLSVersion.TLSv1_2;B=urllib.request.Request(url,headers={_A:_B})
	with urllib.request.urlopen(B,timeout=FETCH_TIMEOUT,context=A)as C:return C.read().decode('utf-8',errors=_C)
@tool(description='用 Python 发起 GET 请求并返回响应正文；先尝试 requests，失败则尝试 urllib（TLS 1.2）。')
def fetch_url(url:Annotated[str,'要请求的 URL，支持 http/https']):
	'\n    用 Python 发起 GET 请求并返回响应正文。\n    查询外部接口、API 或网页时优先使用本工具。先尝试 requests，失败则尝试 urllib（TLS 1.2）。\n    ';B=None
	try:return _fetch_with_requests(url)
	except Exception as C:B=C
	try:return _fetch_with_urllib(url)
	except urllib.error.HTTPError as A:D=A.read().decode('utf-8',errors=_C);return f"HTTP 错误: {A.code} {A.reason}\n{D}"
	except urllib.error.URLError as A:return f"请求失败: requests 报错 ({B}); urllib 报错 ({A.reason})"
	except Exception as A:return f"请求失败: requests 报错 ({B}); urllib 报错 ({A})"