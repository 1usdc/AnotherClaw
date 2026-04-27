'\n分身提示词：存于 agents/prompts/{persona_id}.md，不落库。\n格式为 YAML frontmatter（avatar、name）+ 正文（提示词）。\navatar 可为本地文件名（如 female.png）或完整 URL（在线头像）。\n'
_J='utf-8'
_I=True
_H='default'
_G='persona'
_F='avatar'
_E='system_template'
_D='kind'
_C='prompt'
_B='name'
_A=None
import re
from pathlib import Path
from typing import Any
try:import yaml
except ImportError:yaml=_A
BASE_DIR=Path(__file__).resolve().parents[1]
PROMPTS_DIR=BASE_DIR/'agents'/'prompts'
TEMPLATES_DIR=PROMPTS_DIR/'templates'
DEFAULT_PROMPT_BODY='你是友好、专业的数字分身助手，根据当前对话与用户需求进行回复。'
_AGENT_SYSTEM_PROMPT_FALLBACK='你是以「创造力」为核心的助手，能力均通过对话创建技能获得，仅可使用下列工具。\n\n## 工具\n\n**文件与执行**\n- read_file(path)：读取项目内指定路径的文本文件；path 可为相对项目根的路径，如 skills/技能名/SKILL.md。\n- write_file(path, content)：向项目内指定路径写入文本；path 可为相对项目根，如 skills/技能名/SKILL.md、skills/技能名/scripts/main.py；父目录不存在会自动创建。\n- exec_bash(command, working_dir?)：在项目根或指定 working_dir（相对项目根）下执行 shell 命令。SKILL.md 中常见写法如 `python3 {baseDir}/scripts/polymarket.py orders`：**{baseDir} 表示「该技能目录的根目录」**。执行时请将 working_dir 设为该技能目录（如 skills/polymarket），command 中保留 {baseDir} 即可，工具会自动把 {baseDir} 替换为技能目录路径再执行。\n\n**技能发现（目录 skills/技能名/）**\n- list_skill_tree()：列出所有技能及其描述（来自内存中的 frontmatter）。\n- search_skills(query)：按关键词检索技能，缩小候选后再用 read_file 查看或 exec_bash 执行。\n\n**技能读写与执行**：技能的读、写统一用 read_file / write_file。读技能用 read_file(skills/技能名/SKILL.md)；创建技能用 write_file 写入 SKILL.md 和（可选）scripts/main.py。执行时根据 SKILL.md 中的 run、scripts 等说明，在技能目录下用 exec_bash 执行：**working_dir 设为该技能目录（如 skills/polymarket），command 可直接照抄文档中的命令（含 {baseDir}）**。\n\n**技能目录内 Node 依赖（禁止 `npm install`；统一用 pnpm）**\n- 先进入该技能目录（`exec_bash` 时 `working_dir` 设为 `skills/技能名`）。\n- 新增依赖：`pnpm add <包名>`；仅按已有 package.json / 锁文件安装：`pnpm install`。\n- 若未安装 pnpm：先 `npm i -g pnpm`；若 pnpm 过旧或异常：先 `npm i -g pnpm@latest` 升级，再执行上述 `pnpm` 命令。\n\n## 工作流\n\n根据系统注入的「已加载技能」（含 path）用 read_file(path) 查看 SKILL.md，再按文档用 exec_bash 执行；无合适技能时用 write_file 创建 skills/新技能名/SKILL.md 及 scripts/main.py，再按同上方式执行。\n\n## UI 输出（强约束）\n\n如需用户填写参数，直接输出 RJSF 格式的表单描述。表单必须用字段名 `ui_schema`，值是标准 JSON Schema（包含 `type: "object"` 和 `properties` 字段，可选 `required`、`title`、`description`），始终只返回一个 JSON 对象。\n\n示例：\n{"ui_schema":{"title":"表单标题","type":"object","properties":{"name":{"type":"string","title":"姓名"},"level":{"type":"string","title":"等级","enum":["高","中","低"]}},"required":["name"]}}\n\n最后用自然语言总结回复用户。'
def _ensure_prompts_dir():'确保 agents/prompts 目录存在。';PROMPTS_DIR.mkdir(parents=_I,exist_ok=_I);return PROMPTS_DIR
def get_persona_prompt_path(persona_id:str):'\n    获取某分身的提示词文件路径。\n    @param persona_id 分身 ID（如 default 或 uuid）\n    @returns agents/prompts/{persona_id}.md\n    ';_ensure_prompts_dir();A=''.join(A for A in(persona_id or'').strip()if A.isalnum()or A in'-_')or _H;return PROMPTS_DIR/f"{A}.md"
def load_persona_prompt(persona_id:str):
	'\n    从 agents/prompts/{persona_id}.md 加载分身提示词。\n    文件格式：YAML frontmatter (---\\n...---) + 正文。\n    @returns {"avatar": str, "name": str, "prompt": str} 或 None（文件不存在时）\n    ';A=get_persona_prompt_path(persona_id)
	if not A.is_file():return
	try:B=A.read_text(encoding=_J)
	except Exception:return
	return _parse_prompt_file_content(B)
def _parse_prompt_file_content(raw:str):
	'\n    解析提示词文件内容：首段 YAML frontmatter + 正文。\n    @returns {"avatar": str, "name": str, "prompt": str}\n    ';J='---';A=raw;A=(A or'').strip()
	if not A.startswith(J):return{_F:'',_B:'',_C:A,_D:_G,_E:''}
	E=A.split(J,2)
	if len(E)<3:return{_F:'',_B:'',_C:A,_D:_G,_E:''}
	B=E[1].strip();K=E[2].strip();C={}
	if yaml and B:
		try:G=yaml.safe_load(B)or{};C=G if isinstance(G,dict)else{}
		except Exception:pass
	D=(C.get(_D)or'').strip().lower()
	if not D and B:
		H=re.search('(?m)^kind:\\s*[\\"\']?([A-Za-z0-9_-]+)',B)
		if H:D=H.group(1).lower()
	if not D:D=_G
	F=(C.get(_E)or'').strip()
	if not F and B:
		I=re.search('(?m)^system_template:\\s*[\\"\']?([A-Za-z0-9_-]+)',B)
		if I:F=I.group(1).strip()
	return{_F:(C.get(_F)or'').strip(),_B:(C.get(_B)or'').strip(),_C:K,_D:D,_E:F}
def save_persona_prompt(persona_id:str,prompt:str|_A=_A,avatar:str|_A=_A,name:str|_A=_A,system_template:str|_A=_A):
	'\n    保存分身提示词到 agents/prompts/{persona_id}.md。\n    prompt/avatar/name/system_template 为 None 时保留原有值。\n    system_template 为 agents/prompts/templates/{id}.md 的文件名（不含 .md），空表示 default。\n    @returns 当前完整内容 {"avatar", "name", "prompt", "system_template"}\n    ';M=False;J=system_template;I=avatar;H=prompt;G=persona_id;D=get_persona_prompt_path(G);A=load_persona_prompt(G)if D.is_file()else _A;E=(I if I is not _A else A.get(_F)if A else'')or'';F=(name if name is not _A else A.get(_B)if A else'')or'';C=H if H is not _A else A.get(_C)if A else _A;C=(C or'').strip()or DEFAULT_PROMPT_BODY
	if J is not _A:B=(J or'').strip()
	else:B=(A.get(_E)if A else'')or''
	K={_F:E,_B:F}
	if B:K[_E]=B
	if yaml:L=yaml.dump(K,allow_unicode=_I,default_flow_style=M,sort_keys=M).strip()
	else:L=f"avatar: {repr(E)}\nname: {repr(F)}"+(f"\nsystem_template: {repr(B)}"if B else'')
	N='---\n'+L+'\n---\n\n'+C;D.parent.mkdir(parents=_I,exist_ok=_I);D.write_text(N,encoding=_J);return{_F:E,_B:F,_C:C,_E:B}
def list_prompt_templates():
	'\n    列出 agents/prompts/templates/*.md；含 kind：persona 供「身份提示」导入，kind: agent 供选择工具骨架。\n    @returns [{"id", "name", "content", "kind"}, ...]\n    ';H='默认助手';G='builtin';E='content';D='id';A=[]
	if not TEMPLATES_DIR.is_dir():A.append({D:G,_B:H,E:DEFAULT_PROMPT_BODY,_D:_G});return A
	for B in sorted(TEMPLATES_DIR.glob('*.md')):
		try:F=B.read_text(encoding=_J);C=_parse_prompt_file_content(F);I=(C.get(_B)or'').strip()or B.stem;J=(C.get(_D)or _G).strip().lower()or _G;A.append({D:B.stem,_B:I,E:(C.get(_C)or'').strip()or F,_D:J})
		except Exception:continue
	if not A:A.append({D:G,_B:H,E:DEFAULT_PROMPT_BODY,_D:_G})
	return A
def _safe_template_stem(template_id:str|_A):'模板文件名 stem，仅字母数字、连字符、下划线。';A=(template_id or'').strip();B=''.join(A for A in A if A.isalnum()or A in'-_')or _H;return B
def get_agent_system_prompt_template(template_id:str|_A):
	'\n    加载工具循环用的系统提示骨架：agents/prompts/templates/{template_id}.md 正文。\n    文件不存在时回退 default.md，再回退内置字符串。\n    ';E=_safe_template_stem(template_id);F=[E,_H];B=set()
	for A in F:
		if A in B:continue
		B.add(A);C=TEMPLATES_DIR/f"{A}.md"
		if not C.is_file():continue
		try:
			G=C.read_text(encoding=_J);H=_parse_prompt_file_content(G);D=(H.get(_C)or'').strip()
			if D:return D
		except Exception:continue
	return _AGENT_SYSTEM_PROMPT_FALLBACK
def get_system_template_id_for_persona(persona_id:str|_A):
	'\n    从分身 md 的 frontmatter system_template 读取模板 id；无则 default。\n    ';A=persona_id
	if not(A or'').strip():return _H
	B=load_persona_prompt(A.strip())
	if not B:return _H
	C=(B.get(_E)or'').strip();return _safe_template_stem(C)if C else _H
def get_agent_system_prompt_for_persona(persona_id:str|_A):'\n    按分身配置的 system_template 加载 agents/prompts/templates 下的工具向系统提示骨架。\n    ';A=get_system_template_id_for_persona(persona_id);return get_agent_system_prompt_template(A)
def get_persona_system_prompt(persona_id:str|_A):
	'\n    获取分身系统提示词正文（供 Agent 使用）；无文件或为空时返回 None。\n    ';A=persona_id
	if not(A or'').strip():return
	B=load_persona_prompt(A.strip())
	if not B:return
	C=(B.get(_C)or'').strip();return C if C else _A