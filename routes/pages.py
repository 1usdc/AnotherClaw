'\nSPA 页面路由：为所有前端路由返回 dist/index.html（生产模式），\n或提示使用 Vite 开发服务器（开发模式）。\n'
_A='claw-fe'
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
router=APIRouter(tags=['pages'])
BASE_DIR=Path(__file__).resolve().parents[1]
_frontend_candidate=BASE_DIR.parent/_A
UI_DIR=_frontend_candidate if _frontend_candidate.is_dir()else BASE_DIR/_A
SPA_INDEX=UI_DIR/'dist'/'index.html'
_SPA_ROUTES='/','/home','/learn','/skill','/memory'
_DEV_HTML='<!DOCTYPE html><html><head><meta charset="utf-8"><title>AnotherMe</title></head>\n<body style="font-family:system-ui;padding:48px;text-align:center;color:#555">\n<h2>AnotherMe 开发模式</h2>\n<p>前端未构建。请使用 Vite 开发服务器：</p>\n<pre style="background:#f3f4f6;padding:16px;border-radius:8px;display:inline-block;text-align:left">\ncd claw-fe   # 项目根目录下\npnpm dev\n</pre>\n<p>然后访问 <a href="http://localhost:5173">http://localhost:5173</a></p>\n</body></html>'
def _serve_spa():
	'返回 SPA 入口页面或开发提示。'
	if SPA_INDEX.is_file():return HTMLResponse(content=SPA_INDEX.read_text(encoding='utf-8'))
	return HTMLResponse(_DEV_HTML,status_code=200)
def _register_spa_routes():
	for A in _SPA_ROUTES:
		C='spa_'+(A.strip('/')or'root')
		def B(_r=A):return _serve_spa()
		B.__name__=C;router.add_api_route(A,B,methods=['GET'],response_class=HTMLResponse)
_register_spa_routes()