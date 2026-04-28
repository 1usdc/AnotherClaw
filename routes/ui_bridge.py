'\nUI 参数桥接 WebSocket：\n- 前端连接后接收 ui_schema 请求\n- 前端提交表单值后回传，唤醒后端等待中的 LLM 循环\n'
from fastapi import APIRouter,WebSocket,WebSocketDisconnect
from utils.ui_bridge import ui_bridge_manager
router=APIRouter(tags=['ui-bridge'])
@router.websocket('/ws/ui-bridge')
async def ui_bridge_ws(websocket:WebSocket):
	'首页建立的参数桥接通道。';A=websocket;B=(A.query_params.get('client_id')or'').strip()
	if not B:await A.close(code=1008,reason='missing client_id');return
	await A.accept();ui_bridge_manager.register(B,A)
	try:
		while True:
			C=await A.receive_json();E=(C.get('type')or'').strip();D=(C.get('request_id')or'').strip()
			if not D:continue
			if E=='ui_schema_submit':F=C.get('values');ui_bridge_manager.submit_ui_schema(B,D,F if isinstance(F,dict)else None)
			elif E=='ui_schema_cancel':ui_bridge_manager.submit_ui_schema(B,D,None)
	except WebSocketDisconnect:pass
	finally:ui_bridge_manager.unregister(B)