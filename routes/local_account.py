'\n首次访问注册账号（密码哈希存储），并提供仅本地可访问的重置接口。\n'
from __future__ import annotations
import base64,hashlib,os,uuid
from datetime import datetime,timezone
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field
from utils.db import db_local_account_create,db_local_account_delete_all,db_local_account_exists
router=APIRouter(tags=['local-account'])
class RegisterBody(BaseModel):'首次注册请求体。';username:str=Field(...,min_length=1,max_length=128);password:str=Field(...,min_length=1,max_length=256)
def _is_local_request(request:Request):'仅允许本机回环地址。';A=request;B=(A.client.host if A.client else'')or'';return B in('127.0.0.1','::1','localhost')
def _hash_password(password:str):'使用 PBKDF2-HMAC-SHA256 生成带盐哈希。';C='ascii';A=120000;B=os.urandom(16);D=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),B,A);E=base64.b64encode(B).decode(C);F=base64.b64encode(D).decode(C);return f"pbkdf2_sha256${A}${E}${F}"
@router.get('/api/local-account/status')
def local_account_status():'是否已初始化首个账号。';return{'ok':True,'data':{'initialized':db_local_account_exists()}}
@router.post('/api/local-account/register')
def local_account_register(body:RegisterBody):
	'\n    首次注册账号密码。\n    仅允许首次创建；若已存在则拒绝。\n    ';B='username'
	if db_local_account_exists():raise HTTPException(status_code=409,detail='账号已初始化，不能重复注册')
	A={'id':str(uuid.uuid4()),B:body.username.strip(),'password':_hash_password(body.password),'created_at':datetime.now(timezone.utc).isoformat()}
	if not A[B]:raise HTTPException(status_code=400,detail='username 不能为空')
	db_local_account_create(A);return{'ok':True}
@router.delete('/internal/local-account')
def local_account_reset(request:Request):
	'\n    删除本地账号（重置）。\n    仅允许本地访问。\n    '
	if not _is_local_request(request):raise HTTPException(status_code=403,detail='仅允许本机访问')
	A=db_local_account_delete_all();return{'ok':True,'data':{'deleted':A}}