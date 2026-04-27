'\n技能 API 路由：GET /api/skills\n'
_n=b'PK\x03\x04'
_m='/api/skills/env'
_l='global'
_k='keywords'
_j='clawdbot'
_i='__pycache__'
_h='[^a-zA-Z0-9_\\u4e00-\\u9fa5-]'
_g='slug'
_f='value'
_e='/api/skills'
_d='env'
_c='requires'
_b='"\''
_a='path'
_Z='技能名'
_Y='/.'
_X='__MACOSX'
_W='skill'
_V='source'
_U='https://'
_T='```'
_S='^---\\s*\\n(.*?)\\n---\\s*\\n?'
_R='skills'
_Q='content'
_P='type'
_O='message'
_N='imported'
_M='key'
_L='http://'
_K=False
_J='skill_name'
_I='ok'
_H='..'
_G='utf-8'
_F='SKILL.md'
_E='.'
_D='\\'
_C=None
_B='/'
_A=True
import io,json,mimetypes,os,re,subprocess,sys,tarfile,tempfile,zipfile
from pathlib import Path
from urllib.parse import parse_qs,quote,urlparse
import requests
from fastapi import APIRouter,HTTPException,Query,Request
from fastapi.responses import FileResponse,StreamingResponse
from pydantic import BaseModel
from utils.db import db_env_apply_all_to_environ,db_env_get,db_env_set
from utils.skill import get_skill_frontmatter_cache,get_skill_ratings_list,is_valid_env_key,merge_env_with_skill_dotenv,read_skill_env_value,refresh_skill_frontmatter_cache,resolve_skill_dir,skill_env_has_key,write_skill_env_key
router=APIRouter(tags=[_R])
class SkillUpdateBody(BaseModel):'更新技能内容请求体';skill_name:str;content:str;path:str=_F
class SkillAiEditBody(BaseModel):'AI 修改文件请求体';skill_name:str;path:str;content:str;instruction:str
class SkillInstallBody(BaseModel):'从链接安装技能请求体：slug 必填（用于 skills/<slug> 目录名）；clawhub_url 可选（页地址，未传 download_url 时用其拼接 /download）；download_url / version 可选。';slug:str;clawhub_url:str|_C=_C;download_url:str|_C=_C;version:str|_C=_C
class ImportFromUrlBody(BaseModel):'通过下载链接导入技能包：download_url 必填，需为 zip/tar.gz 且包内含 SKILL.md。';download_url:str
class EnvSetBody(BaseModel):'设置环境变量请求体（key 可选以避免漏传时 422，由视图返回 400）';key:str|_C=_C;value:str=''
BASE_DIR=Path(__file__).resolve().parents[1]
SKILLS_ROOT=BASE_DIR/_R
def _ratings_list_to_dict(ratings:list):
	'将评分数组转为 key -> rating 字典，供 get_skill_tree 使用。';B='skill_key';C={}
	for A in ratings:
		if not isinstance(A,dict)or not A.get(B):continue
		D=A.get(B);C[D]={A:C for(A,C)in A.items()if A!=B}
	return C
def _extract_purpose(skill_md_path:Path):
	'从 SKILL.md 提取用途：优先 frontmatter description，其次正文首个有效标题/段落。';H='...';F=skill_md_path
	if not F.is_file():return''
	try:
		A=F.read_text(encoding=_G);B=re.match(_S,A,flags=re.DOTALL)
		if B:
			I=B.group(1);G=re.search('^\\s*description\\s*:\\s*(.+?)\\s*$',I,flags=re.MULTILINE)
			if G:
				C=G.group(1).strip().strip(_b)
				if C:return C[:120]+(H if len(C)>120 else'')
			A=A[B.end():]
		J=[A.strip()for A in A.split('\n')if A.strip()]
		for D in J:
			if D in{'---',_T}:continue
			if re.match('^[`#*_\\-=\\s]+$',D):continue
			E=re.sub('^#+\\s*','',D).strip()
			if E:return E[:120]+(H if len(E)>120 else'')
		return''
	except Exception:return''
def _extract_homepage(skill_md_path:Path):
	'从 SKILL.md frontmatter 提取 homepage URL。';A=skill_md_path
	if not A.is_file():return''
	try:
		E=A.read_text(encoding=_G);B=re.match(_S,E,flags=re.DOTALL)
		if not B:return''
		F=B.group(1);C=re.search('^\\s*homepage\\s*:\\s*(.+?)\\s*$',F,flags=re.MULTILINE)
		if C:
			D=C.group(1).strip().strip(_b)
			if D.startswith((_L,_U)):return D
		return''
	except Exception:return''
def _extract_required_env(skill_md_path:Path):
	'从 SKILL.md frontmatter 的 metadata JSON 中提取 requires.env 列表。';A=skill_md_path
	if not A.is_file():return[]
	try:
		D=A.read_text(encoding=_G);B=re.match(_S,D,flags=re.DOTALL)
		if not B:return[]
		E=B.group(1);C=re.search('^\\s*metadata\\s*:\\s*(.+?)\\s*$',E,flags=re.MULTILINE)
		if not C:return[]
		F=json.loads(C.group(1));G=(F.get(_j)or{}).get(_c)or{};H=G.get(_d)or[];return[A for A in H if isinstance(A,str)and A.strip()]
	except Exception:return[]
def _extract_keywords(skill_md_path:Path):
	'从 SKILL.md frontmatter 提取 keywords（YAML 列表或逗号分隔）。';B=skill_md_path
	if not B.is_file():return[]
	try:
		E=B.read_text(encoding=_G);C=re.match(_S,E,flags=re.DOTALL)
		if not C:return[]
		F=C.group(1);D=re.search('^\\s*keywords\\s*:\\s*(.+?)\\s*$',F,flags=re.MULTILINE)
		if not D:return[]
		A=D.group(1).strip().strip(_b)
		if not A:return[]
		if A.startswith('['):
			try:G=json.loads(A);return[str(A).strip()for A in G if str(A).strip()]
			except Exception:pass
		return[A.strip()for A in A.split(',')if A.strip()]
	except Exception:return[]
def _skill_matches_query(name:str,purpose:str,keywords:list[str],q:str):
	'判断技能是否与检索词 q 匹配（名称、描述或关键词包含 q 的任意分词）。'
	if not(q or'').strip():return _A
	A=' '.join([name,purpose]+keywords).lower();B=[A.strip().lower()for A in q.strip().split()if A.strip()];return all(B in A for B in B)
def _keywords_from_frontmatter(entry:dict):
	'从 frontmatter 条目提取 keywords 列表。';A=entry.get(_k)
	if isinstance(A,str):return[A.strip()for A in A.split(',')if A.strip()]
	if isinstance(A,list):return[str(A).strip()for A in A if str(A).strip()]
	return[]
def _required_env_from_frontmatter(entry:dict):
	'\n    从 frontmatter 条目的 metadata 提取所需环境变量列表。\n    优先支持 metadata.requires.env (PEP 723/OpenClaw 标准)、\n    兼容老的 metadata.clawdbot.requires.env。\n    ';B=entry.get('metadata')or{};C=[]
	if isinstance(B,dict):
		D=B.get(_c)or{}
		if isinstance(D,dict):
			A=D.get(_d)
			if isinstance(A,list):
				C=[A for A in A if isinstance(A,str)and A.strip()]
				if C:return C
		E=B.get(_j)or{}
		if isinstance(E,dict):
			F=E.get(_c)or{};A=F.get(_d)if isinstance(F,dict)else _C
			if isinstance(A,list):return[A for A in A if isinstance(A,str)and A.strip()]
	return[]
def _read_skill_meta_json(skill_dir:Path|_C):
	'\n    若技能目录下存在 ``_meta.json``，解析为字典并返回；不存在或解析失败则返回 ``None``。\n    ';A=skill_dir
	if not A:return
	B=A/'_meta.json'
	if not B.is_file():return
	try:D=B.read_text(encoding=_G);C=json.loads(D)
	except(OSError,json.JSONDecodeError,TypeError):return
	return C if isinstance(C,dict)else _C
@router.get(_e)
def get_skill_tree(q:str=Query('',description='检索关键词，按名称/描述/keywords 过滤本地技能')):
	'\n    返回技能列表：从内存中的 frontmatter 缓存读取，仅包含 skills/ 下含 SKILL.md 的目录。\n    返回 {"skills": [...]}，可选 q：按关键词过滤。\n    若某技能目录存在 ``_meta.json`` 且为 JSON 对象，则在对应条目中包含 ``meta`` 字段。\n    ';N='homepage'
	if not SKILLS_ROOT.is_dir():return{_R:[]}
	E=get_skill_frontmatter_cache();O=get_skill_ratings_list();F=_ratings_list_to_dict(O);G=(q or'').strip();H=[]
	for A in sorted(E.keys()):
		B=E[A];I=(B.get('description')or'').strip();J=_keywords_from_frontmatter(B)
		if G and not _skill_matches_query(A,I,J,G):continue
		P=A;C=F.get(P,{})or F.get(f"local/{A}",{})
		if not isinstance(C,dict):C={}
		Q=(B.get(N)or'').strip();K=_required_env_from_frontmatter(B);D=resolve_skill_dir(SKILLS_ROOT,A);R=[A for A in K if not os.environ.get(A,'').strip()and not(D and skill_env_has_key(D,A))];L={'name':A,'purpose':I,_k:J,'rating':C,N:Q,'required_env':K,'missing_env':R};M=_read_skill_meta_json(D)
		if M is not _C:L['meta']=M
		H.append(L)
	return{_R:H}
@router.get('/api/skills/installed-slugs')
def get_installed_slugs():
	'返回本地已安装的技能 slug 列表（即 skills/ 下含 SKILL.md 的目录名），供前端标记已安装状态。';D='slugs'
	if not SKILLS_ROOT.is_dir():return{D:[]}
	B=[]
	for A in sorted(os.listdir(SKILLS_ROOT)):
		C=SKILLS_ROOT/A
		if C.is_dir()and not A.startswith(_E)and(C/_F).is_file():B.append(A)
	return{D:B}
@router.get(_m)
def get_env_variable(key:str|_C=Query(_C,description='环境变量名'),skill_name:str|_C=Query(_C,description='技能目录名；若提供则从 skills/<name>/.env 读取，不写全局')):
	'获取环境变量：未传 skill_name 时读 SQLite config 表，缺省再读进程环境；传 skill_name 时只读该技能目录下 `.env`。';A=key;A=(A or'').strip()
	if not A or not is_valid_env_key(A):raise HTTPException(status_code=400,detail='环境变量名不合法（需提供 key 查询参数，且为大写字母开头、仅含大写字母/数字/下划线）')
	C=(skill_name or'').strip()
	if C:
		D=resolve_skill_dir(SKILLS_ROOT,C)
		if not D:raise HTTPException(status_code=404,detail=f"技能不存在或无效: {C}")
		B=read_skill_env_value(D,A)
		if not(B or'').strip():B=os.environ.get(A,'')
		return{_M:A,_f:B,_J:C,_V:_W}
	E=db_env_get(A);B=E if E is not _C else os.environ.get(A,'');return{_M:A,_f:B,_V:_l}
@router.post(_m)
async def set_env_variable(request:Request):
	'\n    设置环境变量。\n    - 请求体含 `skill_name` 时：只写入 `skills/<skill_name>/.env`，不修改全局配置。\n    - 否则：写入 ``data/database/sqlite.db`` 的 ``config`` 表，并更新 ``os.environ``（不再写应用根目录 ``.env``）。\n    '
	try:C=await request.json()
	except Exception:C={}
	A=str(C.get(_M)or'').strip();E=str(C.get(_f)or'').strip();D=str(C.get(_J)or'').strip()
	if not A or not is_valid_env_key(A):raise HTTPException(status_code=400,detail='环境变量名不合法（需大写字母开头，仅含大写字母/数字/下划线）')
	if D:
		F=resolve_skill_dir(SKILLS_ROOT,D)
		if not F:raise HTTPException(status_code=404,detail=f"技能不存在或无效: {D}")
		try:write_skill_env_key(F,A,E)
		except OSError as B:raise HTTPException(status_code=500,detail=f"无法写入技能 .env: {B}")from B
		return{_I:_A,_M:A,_J:D,_V:_W}
	try:db_env_set(A,E)
	except Exception as B:raise HTTPException(status_code=500,detail=f"无法写入配置库: {B}")from B
	os.environ[A]=E;return{_I:_A,_M:A,_V:_l}
@router.get('/api/skills/openai-config-check')
def openai_config_check(request:Request):'\n    检查 OpenAI 相关环境变量是否已配置，供前端决定是否弹窗让用户填写。\n    返回 openai_api_key_set、openai_base_url_set（均为 bool）。\n\n    每次请求前从 SQLite 将全局环境变量同步到进程环境，与 ``set_env`` 写入的存储一致。\n    ';db_env_apply_all_to_environ();A=bool((os.getenv('N1N_API_KEY')or os.getenv('OPENAI_API_KEY')or'').strip());B=bool((os.getenv('OPENAI_BASE_URL')or'').strip());return{'openai_api_key_set':A,'openai_base_url_set':B}
CLAWHUB_API_BASE='https://topclawhubskills.com/api'
CLAWHUB_API_TIMEOUT=15
@router.get('/api/skills/online')
def get_online_skills(source:str=Query('newest',description='列表来源：newest 最新 / top-downloads 热门下载 / search 搜索'),limit:int=Query(30,ge=1,le=100,description='返回条数'),q:str=Query('',description='搜索关键词（source=search 时使用）')):
	'\n    从 ClawHub 开源技能库获取技能列表（代理 TopClawHubSkills 公开 API）。\n    返回技能 slug、名称、简介、下载量、星标、ClawHub 详情/下载链接等。\n    ';E=source;D='limit';A=limit
	try:
		if E=='search':B=f"{CLAWHUB_API_BASE}/search";C={'q':q or _W,D:A}
		elif E=='top-downloads':B=f"{CLAWHUB_API_BASE}/top-downloads";C={D:A}
		else:B=f"{CLAWHUB_API_BASE}/newest";C={D:A}
		F=requests.get(B,params=C,timeout=CLAWHUB_API_TIMEOUT);F.raise_for_status();G=F.json();return G
	except requests.RequestException as H:raise HTTPException(status_code=502,detail=f"获取 ClawHub 技能列表失败: {H}")
CLAWHUB_DOWNLOAD_URL='https://wry-manatee-359.convex.site/api/v1/download?slug={slug}'
CLAWHUB_DOWNLOAD_VERSION_URL='https://wry-manatee-359.convex.site/api/v1/download?slug={slug}&version={version}'
CLAWHUB_DOWNLOAD_HEADERS={'User-Agent':'curl/7.88.1','Referer':'https://clawhub.ai/','Accept':'*/*'}
def _clawhub_proxies():
	'从环境变量读取代理（如 VPN 127.0.0.1:7897），供 requests 与 curl 使用。.env 中可设 HTTPS_PROXY=http://127.0.0.1:7897';A=os.environ.get('HTTPS_PROXY')or os.environ.get('https_proxy')or os.environ.get('HTTP_PROXY')or os.environ.get('http_proxy')or'';A=(A or'').strip()
	if not A:return{}
	if not A.startswith((_L,_U)):A=_L+A
	return{'http':A,'https':A}
def _resolve_skill_download_url(slug:str,download_url:str|_C,version:str|_C,clawhub_url:str|_C):
	'\n    解析下载地址：优先 download_url；否则使用 ClawHub Convex 后端的下载 API。\n    clawhub_url 仅用于记录来源，不再拼接 /download（该路径返回 HTML 而非 zip）。\n    ';B=download_url;A=version
	if B and B.strip().startswith((_L,_U)):return B.strip()
	A=(A or'').strip()
	if A and not re.match('^[a-zA-Z0-9._+-]+$',A):raise HTTPException(status_code=400,detail='version 格式非法')
	if A:return CLAWHUB_DOWNLOAD_VERSION_URL.format(slug=slug,version=A)
	return CLAWHUB_DOWNLOAD_URL.format(slug=slug)
def _download_skill_archive(slug:str,download_url:str|_C,version:str|_C,clawhub_url:str|_C=_C):
	'解析下载 URL 并下载，返回压缩包字节。';B=_resolve_skill_download_url(slug,download_url,version,clawhub_url)
	try:
		C=_clawhub_proxies();A=requests.get(B,timeout=60,stream=_A,allow_redirects=_A,headers=CLAWHUB_DOWNLOAD_HEADERS,proxies=C or _C)
		if A.status_code==404:raise HTTPException(status_code=404,detail=f"该技能「{slug}」在 ClawHub 未提供下载（返回 404）。URL: {B}")
		A.raise_for_status();return A.content
	except HTTPException:raise
	except requests.RequestException as D:raise HTTPException(status_code=502,detail=f"下载失败: {D}")
def _extract_archive_to_skill_dir(archive_bytes:bytes,dest_dir:Path,slug:str):
	'\n    将 zip 或 tar.gz 解压到 dest_dir（即 skills/<slug>/）。\n    若压缩包仅含一个顶层目录，则使用该目录内容；否则使用根目录内容。\n    ';I=archive_bytes;F=dest_dir;F.mkdir(parents=_A,exist_ok=_A);M=I[:4]==_n or I[:2]==b'PK'
	if M:
		J=zipfile.ZipFile(io.BytesIO(I),'r')
		try:
			K=J.namelist();E={A.split(_B)[0].split(_D)[0]for A in K if A.strip()}
			if len(E)==1 and next(iter(E))and not next(iter(E)).startswith(_E):
				G=next(iter(E))+_B
				for C in K:
					if C.startswith(G)or C==next(iter(E))+_D:
						A=C[len(G):].replace(_D,_B).strip(_B)
						if not A or A.startswith(_H):continue
						B=F/A
						if C.endswith(_B)or C.endswith(_D):B.mkdir(parents=_A,exist_ok=_A)
						else:B.parent.mkdir(parents=_A,exist_ok=_A);B.write_bytes(J.read(C))
			else:
				for C in K:
					if C.startswith(_X)or _Y in C or'\\.'in C:continue
					A=C.replace(_D,_B).strip(_B)
					if not A or A.startswith(_H):continue
					B=F/A
					if C.endswith(_B)or C.endswith(_D):B.mkdir(parents=_A,exist_ok=_A)
					else:B.parent.mkdir(parents=_A,exist_ok=_A);B.write_bytes(J.read(C))
		finally:J.close()
		return
	N=io.BytesIO(I)
	with tarfile.open(fileobj=N,mode='r:*')as H:
		O=H.getnames();E={A.split(_B)[0].split(_D)[0]for A in O if A.strip()}
		if len(E)==1 and next(iter(E))and not next(iter(E)).startswith(_E):
			L=next(iter(E));G=L+_B
			for D in H.getmembers():
				if D.name==L or not D.name.startswith(G):continue
				A=D.name[len(G):].replace(_D,_B).strip(_B)
				if not A or A.startswith(_H):continue
				B=F/A
				if D.isdir():B.mkdir(parents=_A,exist_ok=_A)
				else:B.parent.mkdir(parents=_A,exist_ok=_A);B.write_bytes(H.extractfile(D).read())
		else:
			for D in H.getmembers():
				if _X in D.name or _Y in D.name:continue
				A=D.name.replace(_D,_B).strip(_B)
				if not A or A.startswith(_H):continue
				B=F/A
				if D.isdir():B.mkdir(parents=_A,exist_ok=_A)
				else:B.parent.mkdir(parents=_A,exist_ok=_A);B.write_bytes(H.extractfile(D).read())
def _download_from_url(url:str):
	'从任意 URL 下载内容，返回字节。';A=url;A=(A or'').strip()
	if not A.startswith((_L,_U)):raise HTTPException(status_code=400,detail='下载链接需以 http:// 或 https:// 开头')
	try:B=requests.get(A,timeout=60,stream=_A,allow_redirects=_A);B.raise_for_status();return B.content
	except requests.RequestException as C:raise HTTPException(status_code=502,detail=f"下载失败: {C}")
_URL_SLUG_BLACKLIST=frozenset({'download','downloads','api','v1','archive','releases','files','raw','repos','repo'})
def _parse_slug_from_url(url:str):
	'\n    从下载链接中解析出技能 slug，不使用 download 等无效片段。\n    优先：查询参数 slug= 或 skill=；其次路径中最后一个有效片段；若末段为 download 则取其前一段。\n    ';H=urlparse(url);C=parse_qs(H.query)
	for D in(_g,_W,'name'):
		if D in C and C[D]and C[D][0].strip():
			J=C[D][0].strip();A=re.sub(_h,'_',J).strip('_')
			if A and A.lower()not in _URL_SLUG_BLACKLIST and len(A)<=120:return A
	I=(H.path or'').strip(_B)
	if not I:return _N
	E=[A for A in I.split(_B)if A and A.strip()]
	if not E:return _N
	F=E[-1];B=Path(F).stem if _E in F else F;B=B.strip()
	if B.lower()in _URL_SLUG_BLACKLIST and len(E)>=2:G=E[-2];B=Path(G).stem if _E in G else G
	if not B or B.lower()in _URL_SLUG_BLACKLIST:return _N
	A=re.sub(_h,'_',B).strip('_');return A if A and len(A)<=120 else _N
def _validate_skill_archive_and_slug(archive_bytes:bytes,url:str):
	'\n    校验压缩包是否为技能包格式（含 SKILL.md），并返回用于目录名的 slug。\n    若仅有一个顶层目录且其内含 SKILL.md，slug 取该目录名；否则从 URL 解析 slug（不用 download 等）。\n    ';D=archive_bytes
	if len(D)<4:raise HTTPException(status_code=400,detail='下载内容过短，不是有效的 zip 或 tar.gz')
	J=D[:4]==_n or D[:2]==b'PK';E=_K;C=_C
	if J:
		with zipfile.ZipFile(io.BytesIO(D),'r')as K:
			F=[A.replace(_D,_B)for A in K.namelist()if A.strip()];A={A.split(_B)[0].strip()for A in F if not A.startswith(_X)and _Y not in A};A.discard('')
			for G in F:
				if G.rstrip(_B).endswith(_F)or G.strip(_B)==_F:
					E=_A
					if len(A)==1:C=next(iter(A))
					break
			if len(A)==1 and C is _C and E:C=next(iter(A))
	else:
		try:
			L=io.BytesIO(D)
			with tarfile.open(fileobj=L,mode='r:*')as M:
				H=[A.replace(_D,_B)for A in M.getnames()if A.strip()and _X not in A and _Y not in A];A={A.split(_B)[0].strip()for A in H};A.discard('')
				for I in H:
					if I.rstrip(_B).endswith(_F)or I.strip(_B)==_F:
						E=_A
						if len(A)==1:C=next(iter(A))
						break
		except tarfile.ReadError:raise HTTPException(status_code=400,detail='不是有效的 tar/tar.gz 格式')
	if not E:raise HTTPException(status_code=400,detail='不是有效的技能包格式，需包含 SKILL.md')
	if C:
		B=re.sub(_h,'_',C).strip('_')
		if not B or B.lower()in _URL_SLUG_BLACKLIST:B=_parse_slug_from_url(url)
	else:B=_parse_slug_from_url(url)
	if not B or len(B)>120:B=_N
	return B
@router.post('/api/skills/import-from-url')
def import_skill_from_url(body:ImportFromUrlBody):
	'\n    通过下载链接导入技能包：下载 zip/tar.gz，校验内含 SKILL.md，解压到 skills/<slug>。\n    slug 由包内单层目录名或 URL 文件名决定；若该技能已存在返回 409。\n    ';C=_download_from_url(body.download_url);A=_validate_skill_archive_and_slug(C,body.download_url)
	if any(B in A for B in(_B,_D,_H,'\x00')):raise HTTPException(status_code=400,detail='解析出的技能名非法')
	SKILLS_ROOT.mkdir(parents=_A,exist_ok=_A);B=SKILLS_ROOT/A
	if B.exists()and any(B.iterdir()):raise HTTPException(status_code=409,detail=f"技能「{A}」已存在，请先删除或更换下载包")
	try:_extract_archive_to_skill_dir(C,B,A)
	except(zipfile.BadZipFile,tarfile.ReadError,OSError)as D:
		if B.exists():import shutil as E;E.rmtree(B,ignore_errors=_A)
		raise HTTPException(status_code=400,detail=f"解压失败: {D}")
	refresh_skill_frontmatter_cache();return{_I:_A,_O:f"已导入技能: {A}",_g:A}
@router.post('/api/skills/install')
def install_skill_from_clawhub(body:SkillInstallBody):
	'\n    从链接安装技能到本地 skills 目录。\n    不传 download_url 时使用 ClawHub Convex 后端下载 API。支持 zip/tar.gz，自动跟随重定向。\n    ';C=body;A=(C.slug or'').strip()
	if not A or any(B in A for B in(_B,_D,_H,'\x00')):raise HTTPException(status_code=400,detail='slug 非法')
	SKILLS_ROOT.mkdir(parents=_A,exist_ok=_A);B=SKILLS_ROOT/A
	if B.exists()and any(B.iterdir()):raise HTTPException(status_code=409,detail=f"技能 {A} 已存在，请先删除或更换名称")
	try:D=_download_skill_archive(A,C.download_url,C.version,C.clawhub_url)
	except HTTPException:raise
	if len(D)<4:raise HTTPException(status_code=400,detail='下载内容为空或过短')
	try:_extract_archive_to_skill_dir(D,B,A)
	except(zipfile.BadZipFile,tarfile.ReadError,OSError)as E:
		if B.exists():import shutil as F;F.rmtree(B,ignore_errors=_A)
		raise HTTPException(status_code=400,detail=f"解压失败，请确认链接为 zip 或 tar.gz: {E}")
	refresh_skill_frontmatter_cache();return{_I:_A,_O:f"已安装技能: {A}",_g:A}
def _validate_skill_path(skill_name:str):
	'校验 skill_name 非法则抛 HTTPException。';A=skill_name
	if any(B in A for B in(_H,_B,_D))or not A.strip():raise HTTPException(status_code=400,detail='skill_name 非法')
def _skill_dir(skill_name:str):'技能目录：skills/技能名/。';return SKILLS_ROOT/skill_name
def _resolve_file_path(skill_dir:Path,rel_path:str):
	'解析相对路径，确保在 skill_dir 内，否则抛 400。';C=skill_dir;A=rel_path
	if not A or _H in A:raise HTTPException(status_code=400,detail='path 非法')
	B=(C/A).resolve();D=C.resolve()
	if not str(B).startswith(str(D))and B!=D:raise HTTPException(status_code=400,detail='path 越界')
	return B
def _build_skill_file_route(skill_name:str,rel_path:str):'生成前端可直接访问的技能文件路由：/api/skill-routes/{skill_name}/{path}';return'/api/skill-routes/'+quote(skill_name,safe='')+_B+quote(rel_path,safe=_B)
def _is_executable_script_path(rel_path:str):'\n    判定是否为可执行脚本路径。\n    当前按技能执行约定，仅 scripts/main.py 视为可执行入口。\n    ';A=rel_path.replace(_D,_B).strip(_B);return A=='scripts/main.py'
@router.get('/api/skills/files')
def get_skill_files(skill_name:str=Query(...,description=_Z)):
	'获取技能目录下所有文件列表（递归，相对路径）。';A=skill_name;_validate_skill_path(A);B=_skill_dir(A)
	if not B.is_dir():raise HTTPException(status_code=404,detail=f"技能 {A} 不存在")
	C=[]
	for(K,D,L)in os.walk(B):
		D[:]=[A for A in D if not A.startswith(_E)and A!=_i];M=Path(K)
		try:G=M.relative_to(B)
		except ValueError:continue
		H=str(G)+_B if str(G)!=_E else''
		for E in sorted(D):
			if E.startswith(_E)or E==_i:continue
			C.append({_a:H+E,_P:'dir'})
		for I in sorted(L):
			if I.startswith(_E):continue
			F=H+I;J={_a:F,_P:'file'}
			if _is_executable_script_path(F):J['route']=_build_skill_file_route(A,F)
			C.append(J)
	return{_J:A,'files':C}
@router.api_route('/api/skill-routes/{skill_name}/{file_path:path}',methods=['GET','POST'])
async def get_skill_file_content(request:Request,skill_name:str,file_path:str):
	'\n    通过技能路由访问可执行脚本：\n    - GET：读取脚本内容\n    - POST：执行脚本（body 可传 {"args": {...}} 或直接传参数对象）\n    ';N='PYTHONPATH';M='args';I=request;H=skill_name;B=file_path;_validate_skill_path(H)
	if not _is_executable_script_path(B):raise HTTPException(status_code=404,detail=f"仅支持可执行脚本路由: {B}")
	C=_skill_dir(H)
	if not C.is_dir():raise HTTPException(status_code=404,detail=f"技能 {H} 不存在")
	D=_resolve_file_path(C,B)
	if not D.is_file():raise HTTPException(status_code=404,detail=f"文件不存在: {B}")
	if I.method=='GET':O,T=mimetypes.guess_type(str(D));return FileResponse(path=str(D),media_type=O or'application/octet-stream')
	A={}
	try:
		J=await I.json()
		if isinstance(J,dict):A=J
	except Exception:A={}
	K=A.get(M)if isinstance(A.get(M),dict)else A;P=K if isinstance(K,dict)else{};E=_C
	try:
		with tempfile.NamedTemporaryFile(mode='w',suffix='.json',delete=_K,encoding=_G)as L:json.dump(P,L,ensure_ascii=_K);E=L.name
		F=merge_env_with_skill_dotenv(str(C.resolve()),dict(os.environ));F['SKILL_ARGS_JSON']=E;F[N]=os.pathsep.join([str(BASE_DIR),F.get(N,'')]);G=subprocess.run([sys.executable,str(D.resolve())],cwd=str(C.resolve()),env=F,capture_output=_A,text=_A,timeout=60);Q=(G.stdout or'').strip();R=(G.stderr or'').strip();return{_I:G.returncode==0,'exit_code':G.returncode,'output':Q,'error':R}
	except subprocess.TimeoutExpired:raise HTTPException(status_code=504,detail='脚本执行超时（60 秒）')
	except Exception as S:raise HTTPException(status_code=500,detail=f"脚本执行失败: {S}")
	finally:
		if E:
			try:os.unlink(E)
			except Exception:pass
@router.get('/api/skills/file')
def get_skill_file(skill_name:str=Query(...,description=_Z),path:str=Query(...,description='相对技能目录的文件路径，如 SKILL.md、scripts/main.py')):
	'获取技能目录下指定文件内容。仅支持文本文件。';B=path;A=skill_name;_validate_skill_path(A);C=_skill_dir(A)
	if not C.is_dir():raise HTTPException(status_code=404,detail=f"技能 {A} 不存在")
	D=_resolve_file_path(C,B)
	if not D.is_file():raise HTTPException(status_code=404,detail=f"文件不存在: {B}")
	try:E=D.read_text(encoding=_G,errors='replace')
	except Exception as F:raise HTTPException(status_code=500,detail=f"读取失败: {F}")
	return{_J:A,_a:B,_Q:E}
@router.get('/api/skills/routes')
def get_skill_routes():
	'\n    扫描 skills/技能名/ 目录，返回每个可执行脚本对应的前端可访问路由。\n    ';H='routes'
	if not SKILLS_ROOT.is_dir():return{H:[]}
	D=[]
	for A in sorted(os.listdir(SKILLS_ROOT)):
		B=SKILLS_ROOT/A
		if not B.is_dir()or A.startswith(_E)or not(B/_F).is_file():continue
		for(I,E,J)in os.walk(B):
			E[:]=[A for A in E if not A.startswith(_E)and A!=_i];K=Path(I)
			try:F=K.relative_to(B)
			except ValueError:continue
			L=str(F)+_B if str(F)!=_E else''
			for G in sorted(J):
				if G.startswith(_E):continue
				C=L+G
				if not _is_executable_script_path(C):continue
				D.append({_J:A,_a:C,'route':_build_skill_file_route(A,C)})
	return{H:D}
@router.get('/api/skills/detail')
def get_skill_detail(skill_name:str=Query(...,description=_Z)):'获取技能详情：SKILL.md 全文。';return get_skill_file(skill_name=skill_name,path=_F)
@router.put(_e)
def update_skill(body:SkillUpdateBody):
	'更新技能目录下指定文件内容（默认 SKILL.md）。';B=body;A,F,D=B.skill_name,B.content,B.path;_validate_skill_path(A);E=_skill_dir(A)
	if not E.is_dir():raise HTTPException(status_code=404,detail=f"技能 {A} 不存在")
	C=_resolve_file_path(E,D)
	if C.is_dir():raise HTTPException(status_code=400,detail='不能写入目录')
	try:C.parent.mkdir(parents=_A,exist_ok=_A);C.write_text(F,encoding=_G)
	except Exception as G:raise HTTPException(status_code=500,detail=f"写入失败: {G}")
	refresh_skill_frontmatter_cache();return{_I:_A,_O:f"已更新: {A}/{D}"}
@router.delete(_e)
def delete_skill_api(skill_name:str=Query(...,description=_Z)):
	'删除技能目录（skills/技能名/），并清理评分记录。';A=skill_name;_validate_skill_path(A);B=_skill_dir(A)
	if not B.is_dir():raise HTTPException(status_code=404,detail=f"技能 {A} 不存在")
	try:
		C=B.resolve();D=SKILLS_ROOT.resolve()
		if not str(C).startswith(str(D)+os.sep):raise HTTPException(status_code=400,detail='技能路径非法')
		import shutil as E;E.rmtree(C)
	except HTTPException:raise
	except Exception as F:raise HTTPException(status_code=500,detail=f"删除失败: {F}")
	try:from utils.skill import remove_skill_from_ratings as G;G(A)
	except Exception:pass
	refresh_skill_frontmatter_cache();return{_I:_A,_O:f"已删除技能: {A}"}
def _strip_code_fence(text:str):
	'去掉首尾 markdown 代码块包裹。';B=(text or'').strip()
	if not B.startswith(_T):return B
	A=B.split('\n')
	if A[0].startswith(_T):A=A[1:]
	if A and A[-1].strip()==_T:A=A[:-1]
	return'\n'.join(A)
def _stream_ai_edit_events(content:str,instruction:str,path:str):
	'\n    生成 AI 修改的 SSE 流：先逐块推送 type=text，最后推送 type=done（含去壳后的完整内容）。\n    ';G='text';F='role';from agents.base import _get_client as H,_get_model as I;J=H();K=I();L='你是一个文件编辑助手。用户会提供当前文件的完整内容以及修改指令。你必须只输出修改后的完整文件内容，不要输出任何解释、不要用 markdown 代码块包裹。保持原有格式与风格，仅按指令做最小必要修改。';M=f"""当前文件路径：{path}

当前文件内容：
```
{content}
```

用户修改指令：{instruction}""";C=[]
	try:
		N=J.chat.completions.create(model=K,messages=[{F:'system',_Q:L},{F:'user',_Q:M}],temperature=0,stream=_A)
		for D in N:
			E=getattr(D.choices[0],'delta',_C)if D.choices else _C;B=getattr(E,_Q,_C)if E else _C
			if B:C.append(B);A=json.dumps({_P:G,G:B},ensure_ascii=_K);yield f"data: {A}\n\n"
		O=_strip_code_fence(''.join(C));A=json.dumps({_P:'done',_Q:O},ensure_ascii=_K);yield f"data: {A}\n\n"
	except Exception as P:A=json.dumps({_P:'error',_O:str(P)},ensure_ascii=_K);yield f"data: {A}\n\n"
@router.post('/api/skills/ai-edit')
def skill_ai_edit(body:SkillAiEditBody):
	'\n    AI 修改文件内容：流式返回修改后的内容（SSE），前端可逐块更新编辑器。\n    ';A=body;_validate_skill_path(A.skill_name);B=_skill_dir(A.skill_name)
	if not B.is_dir():raise HTTPException(status_code=404,detail=f"技能 {A.skill_name} 不存在")
	if not(A.instruction or'').strip():raise HTTPException(status_code=400,detail='修改指令不能为空')
	return StreamingResponse(_stream_ai_edit_events(A.content or'',A.instruction.strip(),A.path or''),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})