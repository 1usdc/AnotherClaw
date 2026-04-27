'\n定时任务 API：创建、列表、修改（需先暂停）、暂停、删除；后台调度执行。\n'
_Q='/api/tasks/{task_id}'
_P='updated_at'
_O='next_run_at'
_N='/api/tasks'
_M='default'
_L='paused'
_K='active'
_J='提示词不能为空'
_I='interval_seconds'
_H='prompt'
_G='任务不存在'
_F='status'
_E='id'
_D='start_time'
_C='task'
_B='%Y-%m-%dT%H:%M:%SZ'
_A=None
import threading,time,uuid
from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel
from agents.base import optimize_task_prompt_text
from utils import db as tools_db
from routes.chat import _process_message
router=APIRouter(tags=['tasks'])
_SCHEDULER_INTERVAL=60
_scheduler_thread=_A
_scheduler_stop=threading.Event()
def _run_scheduler():
	'后台循环：找出 next_run_at <= now 的 active 任务，执行后更新 next_run_at 或置为 completed。'
	while not _scheduler_stop.wait(_SCHEDULER_INTERVAL):
		try:
			D=datetime.now(timezone.utc).strftime(_B);E=tools_db.db_get_tasks_due(D)
			for A in E:
				try:_process_message(A[_H],persona_id=_M,history=_A,session_id=_A,allow_ui_schema_ws=False)
				except Exception:pass
				B=A.get(_I)or 0;C=datetime.now(timezone.utc).strftime(_B)
				if B>0:F=datetime.now(timezone.utc)+timedelta(seconds=B);G=F.strftime(_B);tools_db.db_update_scheduled_task(A[_E],next_run_at=G,updated_at=C)
				else:tools_db.db_update_scheduled_task(A[_E],status='completed',next_run_at=_A,updated_at=C)
		except Exception:pass
def start_scheduler():
	'启动调度线程（在 lifespan 中调用）。';global _scheduler_thread
	if _scheduler_thread is not _A:return
	_scheduler_stop.clear();_scheduler_thread=threading.Thread(target=_run_scheduler,daemon=True);_scheduler_thread.start()
def stop_scheduler():
	'停止调度线程。';global _scheduler_thread;_scheduler_stop.set()
	if _scheduler_thread:_scheduler_thread.join(timeout=_SCHEDULER_INTERVAL+2)
	_scheduler_thread=_A
class TaskCreate(BaseModel):'创建定时任务请求。';start_time:str;interval_seconds:int=0;prompt:str=''
class TaskUpdate(BaseModel):'修改定时任务请求（需先暂停）。';start_time:str|_A=_A;interval_seconds:int|_A=_A;prompt:str|_A=_A
class TaskTestPromptBody(BaseModel):'调试：用与定时任务相同的方式执行一条提示词（独立会话）。';prompt:str=''
class TaskOptimizePromptBody(BaseModel):'优化定时任务提示词草稿。';prompt:str=''
def _to_iso(s:str):
	'将前端传来的 datetime-local 转为带时区的 ISO 字符串存储。'
	if not s or not s.strip():raise ValueError('start_time 不能为空')
	s=s.strip()
	if'Z'in s or s.endswith('+')or len(s)>=6 and s[-6]in'+-':return s
	if'T'in s:return s+'Z'if len(s)<=19 else s
	return s+'T00:00:00Z'
@router.get(_N)
def list_tasks():'获取所有定时任务列表。';A=tools_db.db_list_scheduled_tasks();return{'tasks':A}
@router.post(_N)
def create_task(body:TaskCreate):
	'创建定时任务。';A=body;B=_to_iso(A.start_time);G=max(0,A.interval_seconds);C=(A.prompt or'').strip()
	if not C:raise HTTPException(status_code=400,detail=_J)
	D=datetime.now(timezone.utc).strftime(_B);E=str(uuid.uuid4());H=B;F={_E:E,_D:B,_I:G,_H:C,_F:_K,_O:H,'created_at':D,_P:D};tools_db.db_create_scheduled_task(F);return{_E:E,_C:F}
@router.put(_Q)
def update_task(task_id:str,body:TaskUpdate):
	'修改定时任务（仅当状态为 paused 时可修改）。';C=task_id;A=body;D=tools_db.db_get_scheduled_task(C)
	if not D:raise HTTPException(status_code=404,detail=_G)
	if D.get(_F)!=_L:raise HTTPException(status_code=400,detail='请先暂停任务后再修改')
	E=datetime.now(timezone.utc).strftime(_B);B={_P:E}
	if A.start_time is not _A:B[_D]=_to_iso(A.start_time)
	if A.interval_seconds is not _A:B[_I]=max(0,A.interval_seconds)
	if A.prompt is not _A:B[_H]=A.prompt.strip()
	if A.start_time is not _A or A.interval_seconds is not _A:F=B.get(_D,D[_D]);B[_O]=F
	tools_db.db_update_scheduled_task(C,**B);return{_C:tools_db.db_get_scheduled_task(C)}
@router.post('/api/tasks/{task_id}/pause')
def pause_task(task_id:str):
	'暂停定时任务。';A=task_id;B=tools_db.db_get_scheduled_task(A)
	if not B:raise HTTPException(status_code=404,detail=_G)
	if B.get(_F)!=_K:return{_C:B}
	C=datetime.now(timezone.utc).strftime(_B);tools_db.db_update_scheduled_task(A,status=_L,updated_at=C);return{_C:tools_db.db_get_scheduled_task(A)}
@router.post('/api/tasks/{task_id}/resume')
def resume_task(task_id:str):
	'恢复定时任务（将 next_run_at 设为 start_time 或当前时间）。';B=task_id;A=tools_db.db_get_scheduled_task(B)
	if not A:raise HTTPException(status_code=404,detail=_G)
	if A.get(_F)!=_L:return{_C:A}
	C=datetime.now(timezone.utc).strftime(_B);D=A.get(_D)or C;tools_db.db_update_scheduled_task(B,status=_K,next_run_at=D,updated_at=C);return{_C:tools_db.db_get_scheduled_task(B)}
@router.delete(_Q)
def delete_task(task_id:str):
	'删除定时任务。';A=tools_db.db_delete_scheduled_task(task_id)
	if not A:raise HTTPException(status_code=404,detail=_G)
	return{'ok':True}
@router.post('/api/tasks/optimize-prompt')
def optimize_prompt(body:TaskOptimizePromptBody):
	'调用大模型将提示词改写得更清晰可执行（不落库、不写入记忆）。';B=(body.prompt or'').strip()
	if not B:raise HTTPException(status_code=400,detail=_J)
	try:C=optimize_task_prompt_text(B)
	except ValueError as A:raise HTTPException(status_code=503,detail=str(A))
	except Exception as A:raise HTTPException(status_code=500,detail=str(A)or'优化失败')
	return{'optimized':C}
@router.post('/api/tasks/test-prompt')
def test_task_prompt(body:TaskTestPromptBody):
	'\n    立即以定时任务同款 Agent 逻辑执行提示词，返回 Agent 回复（不写入定时任务表）。\n    使用 ephemeral：无持久会话、不写会话文件、不写长期记忆。\n    ';A=(body.prompt or'').strip()
	if not A:raise HTTPException(status_code=400,detail=_J)
	try:B=_process_message(A,persona_id=_M,history=_A,session_id=_A,ephemeral=True,allow_ui_schema_ws=False);return B.model_dump()
	except Exception as C:raise HTTPException(status_code=500,detail=str(C)or'执行失败')