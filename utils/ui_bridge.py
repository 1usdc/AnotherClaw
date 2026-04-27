'\nUI 参数桥接：通过 WebSocket 向前端请求表单参数，并在后端线程中阻塞等待用户提交。\n'
_A=None
import asyncio,threading,uuid
from dataclasses import dataclass
from fastapi import WebSocket
@dataclass
class _ClientConn:websocket:WebSocket;loop:asyncio.AbstractEventLoop
class _PendingRequest:
	def __init__(A):A.cond=threading.Condition();A.done=False;A.values=_A
class UiBridgeManager:
	'管理前端 websocket 连接与参数请求/回填。'
	def __init__(A):A._lock=threading.Lock();A._clients={};A._pending={}
	def register(A,client_id:str,websocket:WebSocket):
		B=client_id;C=asyncio.get_running_loop()
		with A._lock:A._clients[B]=_ClientConn(websocket=websocket,loop=C);A._pending.setdefault(B,{})
	def unregister(B,client_id:str):
		C=client_id
		with B._lock:B._clients.pop(C,_A);D=B._pending.pop(C,{})
		for A in D.values():
			with A.cond:A.done=True;A.values=_A;A.cond.notify_all()
	def request_ui_schema(A,client_id:str,*,session_id:str|_A,persona_id:str|_A,schema:dict,timeout_seconds:int=300):
		'\n        发送 ui_schema 请求到前端并阻塞等待用户提交；超时/取消/断开返回 None。\n        可从非异步线程调用。\n        ';C=client_id;D=uuid.uuid4().hex
		with A._lock:
			E=A._clients.get(C)
			if not E:return
			B=_PendingRequest();A._pending.setdefault(C,{})[D]=B
		F={'type':'ui_schema_request','request_id':D,'session_id':session_id,'persona_id':persona_id,'schema':schema}
		try:G=asyncio.run_coroutine_threadsafe(E.websocket.send_json(F),E.loop);G.result(timeout=5)
		except Exception:
			with A._lock:A._pending.get(C,{}).pop(D,_A)
			return
		with B.cond:
			if not B.done:B.cond.wait(timeout=max(1,int(timeout_seconds)))
			H=B.values if B.done else _A
		with A._lock:A._pending.get(C,{}).pop(D,_A)
		return H
	def submit_ui_schema(B,client_id:str,request_id:str,values:dict|_A):
		'前端提交（或取消）后唤醒等待线程。';C=values
		with B._lock:A=B._pending.get(client_id,{}).get(request_id)
		if not A:return False
		with A.cond:A.values=C if isinstance(C,dict)else _A;A.done=True;A.cond.notify_all()
		return True
ui_bridge_manager=UiBridgeManager()