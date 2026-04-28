'\nAnotherMe 入口：加载工具与 Agent，启动前端对话 API（无终端交互，仅在前端对话页交互）。\n'
_C='/assets'
_B='claw-fe'
_A='assets'
import os,sys
from contextlib import asynccontextmanager
from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent
from utils.config_env import init_app_environment
init_app_environment(BASE_DIR)
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from routes import chat,local_account,memory,pages,proxy,sessions,skills,tasks,tts,ui_bridge
@asynccontextmanager
async def lifespan(app:FastAPI):'启动时：确保 data、skills 目录存在；启动定时任务调度；供路由使用应用根目录（库表与配置已在模块加载时初始化）。';A=True;app.state.base_dir=BASE_DIR;(BASE_DIR/'data').mkdir(parents=A,exist_ok=A);(BASE_DIR/'skills').mkdir(parents=A,exist_ok=A);tasks.start_scheduler();yield;tasks.stop_scheduler()
app=FastAPI(title='AnotherMe Chat API',version='0.1.0',lifespan=lifespan)
_frontend_candidate=BASE_DIR.parent/_B
UI_DIR=_frontend_candidate if _frontend_candidate.is_dir()else BASE_DIR/_B
SPA_DIST=UI_DIR/'dist'
if SPA_DIST.is_dir()and(SPA_DIST/_A).is_dir():app.mount(_C,StaticFiles(directory=str(SPA_DIST/_A)),name='spa-assets')
elif(UI_DIR/_A).is_dir():app.mount(_C,StaticFiles(directory=str(UI_DIR/_A)),name='raw-assets')
@app.get('/favicon.ico',include_in_schema=False)
def favicon():
	'返回 favicon，消除浏览器默认请求的 404。';A=UI_DIR/_A/'icons'/'logo.svg'
	if A.is_file():return FileResponse(A,media_type='image/svg+xml')
	return Response(status_code=204)
app.include_router(pages.router)
app.include_router(local_account.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(skills.router)
app.include_router(tts.router)
app.include_router(memory.router)
app.include_router(tasks.router)
app.include_router(ui_bridge.router)
app.include_router(proxy.router)
if __name__=='__main__':
	port=8765;print(f"启动成功: http://localhost:{port}/")
	try:uvicorn.run('main:app',host='0.0.0.0',port=port,reload=False)
	except OSError as e:
		if e.errno==48:print(f"端口 {port} 已占用，查找进程: lsof -i :{port}")
		raise