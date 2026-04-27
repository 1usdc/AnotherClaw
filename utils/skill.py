'\n技能目录、frontmatter 缓存、技能 `.env` 与评分数据：供 API、Agent 与 ``tools.skill_tools`` 复用。\n技能不由后端 subprocess 直接执行：由 Agent 用 read_file 读 SKILL.md、用 exec_bash 执行命令。\n'
_K='keywords'
_J='name'
_I='utf-8'
_H=False
_G='.env'
_F='SKILL.md'
_E='当前无技能。'
_D='\n'
_C=True
_B='description'
_A=None
import os,re
from pathlib import Path
from typing import Any
from dotenv import dotenv_values
try:import yaml
except ImportError:yaml=_A
SKILLS_ROOT='skills'
BASE_DIR=Path(__file__).resolve().parents[1]
_KEY_RE=re.compile('^[A-Z][A-Z0-9_]*$')
def is_valid_env_key(key:str):'是否与全局 API 一致的大写环境变量名。';return bool(key and _KEY_RE.match(key))
def resolve_skill_dir(skills_root:Path,skill_name:str):
	'\n    解析技能目录：须为 skills_root 下真实子目录且含 SKILL.md，禁止路径穿越。\n    @param skills_root - 通常为 claw-be-py/skills\n    @param skill_name - 目录名\n    ';C=skills_root;A=(skill_name or'').strip()
	if not A or'/'in A or'\\'in A or A.startswith('.'):return
	try:B=(C/A).resolve();D=C.resolve()
	except OSError:return
	if B!=D and not str(B).startswith(str(D)+os.sep):return
	if not B.is_dir()or not(B/_F).is_file():return
	return B
def load_skill_dotenv(skill_dir:Path):
	'读取技能目录下 `.env` 为扁平字典（忽略未设置的键）。';B=skill_dir/_G
	if not B.is_file():return{}
	E=dotenv_values(B);C={}
	for(D,A)in E.items():
		if D and A is not _A and str(A).strip()!='':C[D]=str(A)
	return C
def skill_env_has_key(skill_dir:Path,key:str):'某键是否在技能 `.env` 中有非空值。';return bool(load_skill_dotenv(skill_dir).get(key,'').strip())
def read_skill_env_value(skill_dir:Path,key:str):'读取技能 `.env` 中某键的值，不存在则为空字符串。';return load_skill_dotenv(skill_dir).get(key,'')or''
def write_skill_env_key(skill_dir:Path,key:str,value:str):
	'\n    写入或更新技能目录 `.env` 中的单行 KEY=value（保留其余行）。\n    @param value - 原样写入（调用方已校验 key）\n    ';E=value;D=skill_dir;A=key;C=D/_G;D.mkdir(parents=_C,exist_ok=_C);B=[];F=_H
	if C.is_file():
		for G in C.read_text(encoding=_I).splitlines():
			H=G.strip()
			if H.startswith(A+'=')or H.startswith(A+' ='):B.append(f"{A}={E}");F=_C
			else:B.append(G)
	if not F:B.append(f"{A}={E}")
	C.write_text(_D.join(B)+_D,encoding=_I)
def merge_env_with_skill_dotenv(cwd:str|os.PathLike[str],base:dict[str,str]|_A=_A):
	'\n    在 `cwd` 下若存在 `.env`，将其键合并进环境（覆盖 base 中同名键）。\n    用于 exec_bash：在技能目录执行时注入 skills/该技能/.env。\n    ';A=dict(os.environ if base is _A else base);B=Path(cwd)/_G
	if not B.is_file():return A
	for(C,D)in load_skill_dotenv(Path(cwd)).items():A[C]=D
	return A
_skill_frontmatter_cache=_A
def _parse_skill_frontmatter(skill_dir:str):
	'\n    读取技能目录下 SKILL.md 的 frontmatter，解析为字典。\n    返回的 metadata 含 requires.python（列表）与 install（列表）。\n    ';A=os.path.join(skill_dir,_F)
	if not os.path.isfile(A):return{}
	try:B=Path(A).read_text(encoding=_I)
	except Exception:return{}
	if not B.strip().startswith('---'):return{}
	C=re.match('^---\\s*\\n(.*?)\\n---\\s*\\n?',B,flags=re.DOTALL)
	if not C:return{}
	E=C.group(1)
	if not yaml:return{}
	try:D=yaml.safe_load(E);return D if isinstance(D,dict)else{}
	except Exception:return{}
def load_skill_frontmatter_cache(force_refresh:bool=_H):
	'\n    动态加载所有技能的 frontmatter 到内存。\n    扫描 skills/ 下含 SKILL.md 的目录，解析每个 SKILL.md 的 YAML frontmatter，返回 skill_name -> frontmatter 字典。\n    若 force_refresh=True 或缓存未初始化则重新扫描；否则返回已有缓存。\n    ';global _skill_frontmatter_cache
	if _skill_frontmatter_cache is not _A and not force_refresh:return _skill_frontmatter_cache
	C=BASE_DIR/SKILLS_ROOT;B={}
	if not C.is_dir():_skill_frontmatter_cache=B;return B
	for A in sorted(C.iterdir()):
		if not A.is_dir()or A.name.startswith('.')or A.name=='README.md':continue
		E=A/_F
		if not E.is_file():continue
		D=_parse_skill_frontmatter(str(A))
		if D:B[A.name]=D
	_skill_frontmatter_cache=B;return B
def get_skill_frontmatter_cache(force_refresh:bool=_H):'返回技能 frontmatter 缓存（懒加载）。';return load_skill_frontmatter_cache(force_refresh=force_refresh)
def refresh_skill_frontmatter_cache():'在导入或更新技能后调用，使下次读取使用最新 frontmatter。';load_skill_frontmatter_cache(force_refresh=_C)
def get_skill_summaries_for_agent():
	'\n    从内存缓存生成供 Agent 使用的技能摘要列表（name, description, keywords, location），\n    便于技能 prompt 注入：Agent 用 read_file(location) 读 SKILL.md，用 exec_bash 执行。\n    ';F=get_skill_frontmatter_cache();E=[]
	for(B,C)in F.items():
		G=(C.get(_J)or'').strip()or B;H=(C.get(_B)or'').strip();A=C.get(_K)
		if isinstance(A,str):D=[A.strip()for A in A.split(',')if A.strip()]
		elif isinstance(A,list):D=[str(A).strip()for A in A if str(A).strip()]
		else:D=[]
		I=f"{SKILLS_ROOT}/{B}/SKILL.md";E.append({_J:B,'display_name':G,_B:H,_K:D,'location':I})
	return E
SCORE_CRITERIA={_B:(15,'技能描述（frontmatter description 或正文描述）'),'when_to_use':(20,'使用场景（## 使用场景 或等同内容）'),'steps':(25,'步骤与说明（## 步骤与说明 或等同内容）'),'script':(25,'可执行脚本（scripts/main.py 存在）'),'references':(15,'参考资料（references/ 目录存在且含文件）')}
def _load_ratings():'从 SQLite 加载评分列表，格式为 []，每项为 { skill_key, count?, ... }。';from utils.db import db_load_skill_ratings as A;return A()
def get_skill_ratings_list():'供 API 使用：返回评分列表，格式为 [{ skill_key, ... }, ...]。';return _load_ratings()
def remove_skill_from_ratings(skill_key:str):'从评分表中移除指定技能。';from utils.db import db_remove_skill_rating as A;A(skill_key)
def format_skill_line(skill_name:str,description:str):
	'格式化单条技能为 Agent 可读：技能名 + 描述，便于根据描述用 read_file(location) + exec_bash 执行。';A=skill_name;B=(description or'').strip()[:200]
	if B:return f"  - {A}: {B}"
	return f"  - {A}/ (SKILL.md)"
def search_skills_by_keyword(query:str):
	'\n    按关键词/描述检索本地技能，返回与 query 匹配的技能列表（含 frontmatter 描述）。\n    匹配规则：query 按空格分词，每个词需出现在技能名、description 或 keywords 中（不区分大小写）。\n    若 query 为空则返回全部技能（等价 list_skill_tree）。使用内存中的 frontmatter 缓存。\n    ';B=get_skill_frontmatter_cache()
	if not B:
		if not(BASE_DIR/SKILLS_ROOT).is_dir():return f"技能根目录不存在: {SKILLS_ROOT}，可先用 write_file 创建 skills/技能名/SKILL.md 以自动形成目录。"
		return _E
	G=[A.strip().lower()for A in(query or'').strip().split()if A.strip()];C=[]
	for D in sorted(B.keys()):
		E=B[D];I=(E.get(_J)or'').strip()or D;H=(E.get(_B)or'').strip();A=E.get(_K)
		if isinstance(A,str):F=[A.strip()for A in A.split(',')if A.strip()]
		elif isinstance(A,list):F=[str(A).strip()for A in A if str(A).strip()]
		else:F=[]
		J=' '.join([I,H]+F).lower()
		if G and not all(A in J for A in G):continue
		C.append(format_skill_line(D,H))
	return _D.join(C)if C else _E
def list_skill_tree_text():
	'\n    列出技能树的可读文本（与 ``list_skill_tree`` 工具返回一致）。\n    从内存中的 frontmatter 缓存读取各技能名称与描述。\n    ';A=get_skill_frontmatter_cache()
	if not A:
		if not(BASE_DIR/SKILLS_ROOT).is_dir():return f"技能根目录不存在: {SKILLS_ROOT}，可先用 write_file 创建 skills/技能名/SKILL.md 以自动形成目录。"
		return _E
	B=[]
	for C in sorted(A.keys()):D=(A[C].get(_B)or'').strip();B.append(format_skill_line(C,D))
	return _D.join(B)if B else _E