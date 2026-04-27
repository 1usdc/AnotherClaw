'\n聊天 API 路由：POST /api/chat/stream（SSE 流式）\n'
_N='session_id'
_M='prompt'
_L='user_input'
_K='duration'
_J='.,;:!?)'
_I='https?://[^\\s)\\]]+'
_H='请输入内容。'
_G='message'
_F='default'
_E=True
_D=False
_C='content'
_B='step'
_A=None
import json,re,threading
from queue import Empty,Queue
from fastapi import APIRouter,Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents import run_agent_loop,analyze_conversation_for_memory
from utils.memory import add_memory
from utils.session import append_turn,create_session_id,delete_session,get_and_clear_next_open_url,get_step_contents,list_sessions,load_history
from utils.ui_bridge import ui_bridge_manager
router=APIRouter(tags=['chat'])
class ChatResponse(BaseModel):'聊天响应：文本回复、可选超链接、各步骤返回内容、会话 ID。';reply:str;link:str|_A=_A;stepContents:list|_A=_A;session_id:str|_A=_A
def _process_message(user_input:str,persona_id:str|_A=_A,history:list|_A=_A,session_id:str|_A=_A,ephemeral:bool=_D,request_ui_schema=_A,allow_ui_schema_ws:bool=_E):
	'\n    处理用户消息，执行 Agent 循环，返回回复、计时与超链接。\n    若传 session_id 则从会话存储加载历史并追加本轮；否则新建 session_id，使用传入的 history。\n    对话结束后写入当前分身记忆并持久化到会话文件。\n    ephemeral=True：不新建持久会话、不写会话文件、不写记忆（仅本次无状态执行）。\n    ';D=ephemeral;C=user_input;B=session_id;A=history;E=persona_id or _F
	if not C:return ChatResponse(reply=_H,link=_A,stepContents=_A,session_id=_A if D else B)
	if D:B=_A;A=_A
	elif B:
		try:A=load_history(E,B)
		except Exception:A=A or _A
	else:B=create_session_id();A=A if A else _A
	F=run_agent_loop(C,history=A,persona_id=E,request_ui_schema=request_ui_schema if allow_ui_schema_ws else _A);I=get_and_clear_next_open_url()
	if I:H=I
	else:J=re.search(_I,F);H=J.group(0).rstrip(_J)if J else _A
	K,L=get_step_contents();G=_A
	if K and(C or'').strip():
		M={_B:_L,_C:(C or'').strip(),_K:''}
		if L is not _A:M[_M]=L
		G=[M,*K]
	if not D:
		try:append_turn(E,B,C,F,step_contents=G,link=H)
		except Exception:pass
		try:
			O,N=analyze_conversation_for_memory(C,F)
			if O and N:add_memory(E,N)
		except Exception:pass
	return ChatResponse(reply=F,link=H,stepContents=G if G else _A,session_id=_A if D else B)
def _stream_chat_events(user_input:str,persona_id:str|_A=_A,history:list|_A=_A,session_id:str|_A=_A,client_id:str|_A=_A):
	'\n    生成 SSE 事件：先流式推送思考 (thinking)、各步骤 (step)，再流式推送最终回复 (text)，最后推送 done（含 session_id）。\n    若带 session_id 则从存储加载历史；否则新建会话。对话结束后持久化到会话文件并写入记忆。\n    ';W='reply_done';O='thinking';L=client_id;H='type';G='text';D=user_input;C=session_id;B=history;E=persona_id or _F
	if C:
		try:B=load_history(E,C)
		except Exception:B=B or _A
	else:C=create_session_id();B=B if B else _A
	F=Queue();I=[];P=[]
	def X(step_name:str,content):F.put((_B,step_name,content))
	def Y(text_piece:str):F.put((G,text_piece,_A))
	def Z(text_piece:str):A=text_piece;P.append(A);F.put((O,A,_A))
	def a():
		try:
			def A(schema:dict):
				if not L:return
				return ui_bridge_manager.request_ui_schema(L,session_id=C,persona_id=E,schema=schema)
			G=run_agent_loop(D,history=B,on_step=X,on_text_delta=Y,on_thinking_delta=Z,persona_id=E,request_ui_schema=A if L else _A);I.append(G)
		except Exception as H:I.append(f"错误: {H}")
		finally:F.put((W,_A,_A))
	threading.Thread(target=a,daemon=_E).start()
	while _E:
		try:J,M,b=F.get(timeout=60)
		except Empty:A=json.dumps({H:'error',_G:'timeout'});yield f"data: {A}\n\n";return
		if J==_B:A=json.dumps({H:_B,_B:M,_C:b},ensure_ascii=_D);yield f"data: {A}\n\n"
		elif J==O:A=json.dumps({H:O,G:M},ensure_ascii=_D);yield f"data: {A}\n\n"
		elif J==G:A=json.dumps({H:G,G:M},ensure_ascii=_D);yield f"data: {A}\n\n"
		elif J==W:break
	c=I[0]if I else'';K=c;d=get_and_clear_next_open_url();Q=re.search(_I,K);R=d or(Q.group(0).rstrip(_J)if Q else _A);S,T=get_step_contents();N=_A
	if S and(D or'').strip():
		U={_B:_L,_C:(D or'').strip(),_K:''}
		if T is not _A:U[_M]=T
		N=[U,*S]
	try:e=''.join(P).strip()or _A;append_turn(E,C,D,K,step_contents=N,link=R,thinking_content=e)
	except Exception:pass
	try:
		f,V=analyze_conversation_for_memory(D,K)
		if f and V:add_memory(E,V)
	except Exception:pass
	A=json.dumps({H:'done','reply':K,'link':R,'stepContents':N,_N:C},ensure_ascii=_D);yield f"data: {A}\n\n"
@router.post('/api/chat/stream')
async def chat_stream(request:Request):
	'\n    流式聊天：SSE 先推送中间步骤 (step)，再流式推送最终回复 (text)，最后推送 done（含 link/stepContents/session_id）。\n    带 session_id 时从服务端加载历史；否则新建会话并在 done 中返回 session_id。\n    使用 Request 手动解析 body，避免 build 下 Pydantic 校验导致 422。\n    ';I='user';H='persona_id';D='role'
	try:A=await request.json()
	except Exception:A={}
	J=(A.get(_G)if isinstance(A.get(_G),str)else'')or'';K=A.get(H)if A.get(H)is not _A else _A;E=(A.get(_N)or'').strip()or _A;L=(A.get('client_id')or'').strip()or _A;F=A.get('history');C=[]
	if isinstance(F,list):
		for B in F:
			if not isinstance(B,dict):continue
			C.append({D:B.get(D)or I if isinstance(B.get(D),str)else I,_C:B.get(_C)or''if isinstance(B.get(_C),str)else''})
	G=J.strip()
	if not G:return ChatResponse(reply=_H,link=_A,stepContents=_A,session_id=E)
	return StreamingResponse(_stream_chat_events(G,persona_id=K,history=C if C else _A,session_id=E,client_id=L),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
@router.get('/api/chat/sessions')
def list_chat_sessions(persona_id:str|_A=_A):
	'\n    列出当前分身下的所有会话，按修改时间倒序。\n    返回 { "sessions": [{"session_id", "updated_at", "preview"}, ...] }。\n    ';B=persona_id or _F
	try:A=list_sessions(B)
	except Exception:A=[]
	return{'sessions':A}
@router.delete('/api/chat/session')
def delete_chat_session(persona_id:str|_A=_A,session_id:str|_A=_A):
	'\n    删除指定会话；session_id 必填。返回 { "ok": true } 或 404。\n    ';from fastapi import HTTPException as A;C=persona_id or _F;B=(session_id or'').strip()
	if not B:raise A(status_code=400,detail='session_id 必填')
	if not delete_session(C,B):raise A(status_code=404,detail='会话不存在或已删除')
	return{'ok':_E}