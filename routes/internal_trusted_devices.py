'\n本机或管理员令牌可访问的 UA + 设备指纹管理 API（SSH 登录后 ``curl http://127.0.0.1/...``）。\n'
from __future__ import annotations
_A='user_agent'
import sqlite3,uuid
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import AliasChoices,BaseModel,ConfigDict,Field
from utils.db import db_trusted_device_delete,db_trusted_device_insert,db_trusted_device_list
from utils.trusted_device import HEADER_DEVICE_FINGERPRINT,_normalize_fp,_normalize_ua,admin_request_authorized
router=APIRouter(tags=['internal-trusted-devices'],prefix='/internal/trusted-devices')
def verify_admin(request:Request):
	'依赖：校验本机或管理员令牌。'
	if not admin_request_authorized(request):raise HTTPException(status_code=403,detail='仅允许从本机访问，或设置环境变量 DEVICE_AUTH_ADMIN_TOKEN 并在请求头携带 X-Device-Auth-Admin-Token（例如经反向代理时）。')
class TrustedDeviceCreate(BaseModel):'登记一条 User-Agent + 设备指纹。';model_config=ConfigDict(populate_by_name=True);user_agent:str=Field(...,min_length=1,description='与浏览器请求 User-Agent 一致',validation_alias=AliasChoices(_A,'userAgent'));fingerprint:str=Field(...,min_length=1,description='与请求头 X-Device-Fingerprint 或 WS 参数 device_fingerprint 一致');note:str=Field('',description='可选备注')
@router.get('',dependencies=[Depends(verify_admin)])
def list_trusted_devices():'列出已登记设备。';return{'items':db_trusted_device_list()}
@router.post('',dependencies=[Depends(verify_admin)])
def add_trusted_device(body:TrustedDeviceCreate):
	'新增登记；同一 UA + 指纹对已存在时返回 409。';B=body;C=_normalize_ua(B.user_agent);D=_normalize_fp(B.fingerprint)
	if not C or not D:raise HTTPException(status_code=400,detail='user_agent 与 fingerprint 不能为空')
	E={'id':str(uuid.uuid4()),_A:C,'fingerprint':D,'note':(B.note or'').strip(),'created_at':datetime.now(timezone.utc).isoformat()}
	try:db_trusted_device_insert(E)
	except sqlite3.IntegrityError as A:
		if'UNIQUE constraint failed'in str(A)or'unique constraint'in str(A).lower():raise HTTPException(status_code=409,detail='该 user_agent + fingerprint 已存在')from A
		raise HTTPException(status_code=400,detail=str(A))from A
	return{'ok':True}
@router.delete('/{device_id}',dependencies=[Depends(verify_admin)])
def remove_trusted_device(device_id:str):
	'按 id 删除登记。';A=(device_id or'').strip()
	if not A:raise HTTPException(status_code=400,detail='device_id 无效')
	if not db_trusted_device_delete(A):raise HTTPException(status_code=404,detail='未找到该 id')
	return{'ok':True}
@router.get('/help-headers',include_in_schema=False)
def help_headers():'说明客户端需携带的头（无需认证，便于调试）。';return{'http_header_ua':'User-Agent（浏览器自动发送）','http_header_fingerprint':HEADER_DEVICE_FINGERPRINT,'websocket':'请求头 User-Agent + 查询参数 device_fingerprint','admin':'GET/POST/DELETE /internal/trusted-devices 需本机 IP 或 X-Device-Auth-Admin-Token'}