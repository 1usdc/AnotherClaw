'\n记忆与分身：data/memory/{persona_id}/ 下存放\n- _meta.json：分身元数据（id、name、avatar、created_at）；\n- MEMORY.md、YYYY-MM-DD.md：记忆条目。\n'
_P='avators'
_O='assets'
_N='claw-fe'
_M='MEMORY.md'
_L='updated_at'
_K='persona_id'
_J='content'
_I=False
_H='created_at'
_G='\n'
_F='utf-8'
_E='name'
_D=True
_C='avatar'
_B='id'
_A=None
import json,os,random,re,uuid
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from utils.prompt import save_persona_prompt as _save_persona_prompt
BASE_DIR=Path(__file__).resolve().parents[1]
DATA_DIR=BASE_DIR/'data'
MEMORY_DIR=DATA_DIR/'memory'
PERSONA_META_FILENAME='_meta.json'
_frontend_candidate=BASE_DIR.parent/_N
_frontend_dir=_frontend_candidate if _frontend_candidate.is_dir()else BASE_DIR/_N
_avatar_candidates=_frontend_dir/_O/_P,_frontend_dir/'dist'/_O/_P
UI_AVATAR_DIR=next((A for A in _avatar_candidates if A.is_dir()),_avatar_candidates[0])
DEFAULT_PERSONA_ID='default'
DEFAULT_AVATAR='female.png'
_MEMORY_LINE_PATTERN=re.compile('^-\\s+([a-f0-9]+)\\t([^\\t]+)\\t(.*)$',re.DOTALL)
def _persona_memory_dir(persona_id:str):'某分身的记忆目录：data/memory/{persona_id}/';B=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;A=MEMORY_DIR/B;A.mkdir(parents=_D,exist_ok=_D);return A
def _persona_meta_path(persona_id:str):'分身元数据路径：data/memory/{persona_id}/_meta.json';A=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;return MEMORY_DIR/A/PERSONA_META_FILENAME
def _read_persona_meta(persona_id:str):
	'读取 _meta.json；不存在或解析失败返回 None。';A=_persona_meta_path(persona_id)
	if not A.is_file():return
	try:
		B=json.loads(A.read_text(encoding=_F))
		if not isinstance(B,dict):return
		return B
	except Exception:return
def _write_persona_meta(rec:dict[str,Any]):
	'写入 data/memory/{id}/_meta.json（原子替换）。';B=(rec.get(_B)or'').strip()
	if not B:return
	A=_persona_meta_path(B);A.parent.mkdir(parents=_D,exist_ok=_D);D=json.dumps(rec,ensure_ascii=_I,indent=2)+_G;C=A.with_suffix('.tmp');C.write_text(D,encoding=_F);C.replace(A)
def _now_iso():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _load_personas_from_disk():
	'扫描 memory/*/ _meta.json，按 created_at 升序。';C=[]
	if not MEMORY_DIR.is_dir():return C
	for D in MEMORY_DIR.iterdir():
		if not D.is_dir():continue
		B=D.name;A=_read_persona_meta(B)
		if not A or not(A.get(_E)or'').strip():continue
		E=(A.get(_B)or B).strip()or B
		if E!=B:A[_B]=B
		else:A[_B]=E
		C.append(A)
	C.sort(key=lambda x:x.get(_H)or'');return C
def _parse_memory_line(line:str,persona_id:str):
	'解析一行记忆，返回 {id, persona_id, content, created_at, updated_at} 或 None。';A=line;A=A.strip()
	if not A or not A.startswith('-'):return
	B=_MEMORY_LINE_PATTERN.match(A)
	if not B:return
	D,C,E=B.group(1),B.group(2),B.group(3);return{_B:D,_K:persona_id,_J:E,_H:C,_L:C}
def _read_memories_from_file(path:Path,persona_id:str):
	'从单个 .md 文件读取所有记忆行。';A=[]
	if not path.is_file():return A
	try:
		C=path.read_text(encoding=_F)
		for D in C.splitlines():
			B=_parse_memory_line(D,persona_id)
			if B:A.append(B)
	except Exception:pass
	return A
def _append_memory_line(path:Path,mid:str,created_at:str,content:str):
	'向文件追加一行记忆；内容中的换行替换为空格。';A=(content or'').replace(_G,' ').strip();B=f"- {mid}\t{created_at}\t{A}\n";path.parent.mkdir(parents=_D,exist_ok=_D)
	with path.open('a',encoding=_F)as C:C.write(B)
def _find_memory_line(memory_id:str):
	'在 data/memory 下查找包含该 id 的文件、行号与整行内容；未找到返回 None。'
	if not MEMORY_DIR.is_dir():return
	for A in MEMORY_DIR.iterdir():
		if not A.is_dir():continue
		F=A.name
		for B in A.glob('*.md'):
			try:
				D=B.read_text(encoding=_F).splitlines()
				for(E,C)in enumerate(D):
					if C.strip().startswith(f"- {memory_id}\t"):return B,E,C
			except Exception:continue
def get_avatar_options():
	'返回 avators 目录下内置头像文件名列表（如 female.png、01.svg）。'
	if not UI_AVATAR_DIR.is_dir():return[]
	B=[]
	for A in UI_AVATAR_DIR.iterdir():
		if A.is_file()and A.suffix.lower()in('.svg','.png','.jpg','.jpeg','.webp'):B.append(A.name)
	return sorted(B)
def load_memories(persona_id:str|_A=_A):
	'\n    从 data/memory/{persona_id}/ 加载记忆：MEMORY.md（长期）+ 按日 YYYY-MM-DD.md，合并后按时间倒序。\n    ';B=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;D=_persona_memory_dir(B);A=[];A.extend(_read_memories_from_file(D/_M,B))
	for C in sorted(D.glob('*.md'),reverse=_D):
		if C.name==_M:continue
		if re.match('^\\d{4}-\\d{2}-\\d{2}\\.md$',C.name):A.extend(_read_memories_from_file(C,B))
	A.sort(key=lambda x:x.get(_H,''),reverse=_D);return A
def format_memories_for_prompt(persona_id:str|_A=_A,max_chars:int|_A=_A):
	'\n    将记忆页已存储条目格式化为可拼入大模型 system 的纯文本（与 load_memories 同源数据）。\n    按创建时间新到旧；总长超过上限时丢弃较旧条目。无条目时返回空串。\n\n    上限默认取环境变量 MEMORY_PROMPT_MAX_CHARS（缺省 12000）。\n    ';D=max_chars
	try:A=D if D is not _A else int(os.getenv('MEMORY_PROMPT_MAX_CHARS','12000'))
	except ValueError:A=12000
	A=max(500,min(A,200000));E=load_memories(persona_id)
	if not E:return''
	B=[];F=0
	for I in E:
		G=(I.get(_J)or'').strip()
		if not G:continue
		C=f"- {G}";H=(_G if B else'')+C
		if F+len(H)>A:
			if not B and len(C)>A:return C[:A-1]+'…'
			break
		B.append(C);F+=len(H)
	return _G.join(B)
def load_personas():
	'从 data/memory/<id>/_meta.json 加载分身列表；首个分身默认头像 female.png。';C='角色1';A=_load_personas_from_disk();A=[A for A in A if A.get(_B)and A.get(_E)];D=set(get_avatar_options())
	if not any(A.get(_B)==DEFAULT_PERSONA_ID for A in A):E={_B:DEFAULT_PERSONA_ID,_E:C,_C:DEFAULT_AVATAR,_H:_now_iso()};A.insert(0,E)
	for B in A:
		if B.get(_B)==DEFAULT_PERSONA_ID and(B.get(_E)or'').strip()=='默认':B[_E]=C;break
	for B in A:
		if not B.get(_C)or B.get(_C)not in D:B[_C]=DEFAULT_AVATAR
	return A
def _id():return uuid.uuid4().hex[:12]
def _random_avatar():'从内置头像列表中随机返回一个文件名；无头像时返回空字符串。';A=get_avatar_options();return random.choice(A)if A else''
def _is_valid_avatar(av:str,opts:list[str]):
	'头像有效：为内置文件名或在线 URL。';A=av
	if not(A or'').strip():return _I
	A=(A or'').strip()
	if A in opts:return _D
	return A.startswith('http://')or A.startswith('https://')
def add_memory(persona_id:str,content:str,memory_id:str|_A=_A,long_term:bool=_I):
	'\n    新增一条记忆，写入 data/memory/{persona_id}/。\n    默认追加到按日文件 YYYY-MM-DD.md；long_term=True 时追加到 MEMORY.md。\n    ';A=content;B=_now_iso();C=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;D=memory_id or _id();A=(A or'').strip();E=_persona_memory_dir(C)
	if long_term:F=E/_M
	else:G=datetime.now(timezone.utc).strftime('%Y-%m-%d');F=E/f"{G}.md"
	_append_memory_line(F,D,B,A);return{_B:D,_K:C,_J:A,_H:B,_L:B}
def update_memory(memory_id:str,content:str):
	'更新一条记忆（在对应 .md 文件中替换该行）。';B=memory_id;E=_find_memory_line(B)
	if not E:return
	C,F,H=E;I=_now_iso();G=(content or'').replace(_G,' ').strip();D=_MEMORY_LINE_PATTERN.match(H.strip())
	if not D:return
	J=f"- {B}\t{D.group(2)}\t{G}\n";A=C.read_text(encoding=_F).splitlines()
	if F>=len(A):return
	A[F]=J.strip();C.write_text(_G.join(A)+(_G if A else''),encoding=_F);return{_B:B,_K:C.parent.name,_J:G,_H:D.group(2),_L:I}
def delete_memory(memory_id:str):
	'删除一条记忆（从对应 .md 文件中移除该行）。';B=_find_memory_line(memory_id)
	if not B:return _I
	C,D,E=B;A=C.read_text(encoding=_F).splitlines()
	if D>=len(A):return _I
	A.pop(D);C.write_text(_G.join(A)+(_G if A else''),encoding=_F);return _D
def append_memory_from_chat(user_input:str,reply:str,persona_id:str|_A=_A,max_content_len:int=2000):
	'\n    根据一轮对话生成并保存一条记忆（简短摘要）。\n    用于对话结束后自动调用。persona_id 为空时使用第一个分身。\n    ';B=max_content_len;C=(user_input or'').strip();A=(reply or'').strip()
	if not C and not A:return
	D=f"用户: {C[:500]}\n助手: {A[:B]}"
	if len(A)>B:D+='...'
	return add_memory(persona_id or DEFAULT_PERSONA_ID,D)
def add_persona(name:str,avatar:str|_A=_A):
	'新增分身，写入 memory/<id>/_meta.json。avatar 可为内置文件名或在线 URL，为空时随机内置头像。';C=_id();D=get_avatar_options();B=(avatar or'').strip()
	if not B or not _is_valid_avatar(B,D):B=_random_avatar()
	A={_B:C,_E:(name or'未命名').strip(),_C:B,_H:_now_iso()};_persona_memory_dir(C);_write_persona_meta(A);_save_persona_prompt(A[_B],prompt=_A,avatar=A[_C],name=A[_E]);return A
def update_persona(persona_id:str,name:str,avatar:str|_A=_A):
	'更新分身名称与头像。第一个分身可改名、改头像，不可删除。avatar 为 None 表示不修改。';C=avatar;B=persona_id;G=get_avatar_options();A=_read_persona_meta(B)
	if A:
		D=_A
		if C is not _A:
			E=(C or'').strip()
			if B==DEFAULT_PERSONA_ID:D=E if _is_valid_avatar(E,G)else A.get(_C)or DEFAULT_AVATAR
			else:D=E if _is_valid_avatar(E,G)else A.get(_C)or _random_avatar()
		H=(name or'未命名').strip();I=D if D is not _A else A.get(_C);A[_E]=H;A[_C]=I;_write_persona_meta(A);_save_persona_prompt(B,prompt=_A,avatar=I,name=H);return{**A,_E:H,_C:I}
	if B==DEFAULT_PERSONA_ID:
		F=(C or'').strip()if C is not _A else DEFAULT_AVATAR
		if not _is_valid_avatar(F,G):F=DEFAULT_AVATAR
		J=(name or'默认').strip();K={_B:DEFAULT_PERSONA_ID,_E:J,_C:F,_H:_now_iso()};_persona_memory_dir(DEFAULT_PERSONA_ID);_write_persona_meta(K);_save_persona_prompt(DEFAULT_PERSONA_ID,prompt=_A,avatar=F,name=J);return K
def delete_persona(persona_id:str):
	'删除分身元数据（移除 _meta.json）；目录内记忆 .md 保留。';A=persona_id
	if A==DEFAULT_PERSONA_ID:return _I
	B=_persona_meta_path(A)
	if not B.is_file():return _I
	B.unlink();return _D