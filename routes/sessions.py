'\n会话 API：按会话读取消息（GET /api/sessions/session）。会话列表由 GET /api/chat/sessions 提供。\n'
_B='.jsonl'
_A=None
import json
from pathlib import Path
from fastapi import APIRouter
from utils.session import SESSIONS_DIR
router=APIRouter(tags=['sessions'])
def _session_file(persona_id:str,session_id:str):
	'返回会话文件路径（.json 或 .jsonl），不存在则 None。';B=SESSIONS_DIR/persona_id
	for C in('.json',_B):
		A=B/f"{session_id}{C}"
		if A.is_file():return A
def _read_session_messages(path:Path):
	'从 .json 或 .jsonl 读取消息列表，每条含 index、role、content、step_contents(可选)、link(可选)。';P='assistant';O='user_input';N='user';M='index';I='content';G='thinking_content';F='link';E='step_contents';D='created_at';C='role';L=path.read_text(encoding='utf-8',errors='replace');J=[]
	if path.suffix==_B:
		for(K,H)in enumerate(L.strip().splitlines(),start=1):
			H=H.strip()
			if not H:continue
			try:
				A=json.loads(H);B={M:K,C:A.get(C,N),I:(A.get(I)or A.get(O)or'').strip()}
				if A.get(D):B[D]=A[D]
				if A.get(C)==P:
					if A.get(E)is not _A:B[E]=A[E]
					if A.get(F)is not _A:B[F]=A[F]
					if A.get(G)is not _A:B[G]=A[G]
				J.append(B)
			except json.JSONDecodeError:continue
	else:
		try:
			Q=json.loads(L);R=Q.get('turns')or[]
			for(K,A)in enumerate(R,start=1):
				B={M:K,C:A.get(C,N),I:(A.get(I)or A.get(O)or'').strip()}
				if A.get(D):B[D]=A[D]
				if A.get(C)==P:
					if A.get(E)is not _A:B[E]=A[E]
					if A.get(F)is not _A:B[F]=A[F]
					if A.get(G)is not _A:B[G]=A[G]
				J.append(B)
		except json.JSONDecodeError:pass
	return J
@router.get('/api/sessions/session')
def get_session_detail(persona_id:str|_A=_A,session_id:str|_A=_A):
	'\n    统一按会话取消息：支持 .json/.jsonl，返回带 index 的 messages。\n    无 session_id 或会话不存在时返回 200 + 空 messages，供恢复聊天与查看会话记录共用。\n    ';E='messages';D='session_id';C='persona_id';A=persona_id or'default';B=(session_id or'').strip()
	if not B:return{C:A,D:_A,E:[]}
	F=_session_file(A,B)
	if not F:return{C:A,D:B,E:[]}
	G=_read_session_messages(F);return{C:A,D:B,E:G}