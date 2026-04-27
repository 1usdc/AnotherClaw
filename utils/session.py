'\n会话持久化与步骤计时/UI：\n- 按 persona_id + session_id 存储对话轮次到 data/sessions/，供聊天路由加载历史与列表/删除。\n- 步骤计时：record_step / get_step_contents、get_timing_report。\n- UI：get_and_clear_next_open_url、extract_ui_schema_payload、strip_ui_schema_from_reply。\n'
_N='```json\\s*([\\s\\S]*?)\\s*```'
_M='session_id'
_L='user_input'
_K='user'
_J='updated_at'
_I='data'
_H='ui_schema'
_G='role'
_F='utf-8'
_E=False
_D='content'
_C='turns'
_B=True
_A=None
import json,re,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,List,Tuple
BASE_DIR=Path(__file__).resolve().parents[1]
SESSIONS_DIR=BASE_DIR/_I/'sessions'
NEXT_OPEN_URL_PATH=BASE_DIR/_I/'next_open_url.json'
_timing_session=_A
def _session_path(persona_id:str,session_id:str):'会话文件路径：data/sessions/{persona_id}/{session_id}.json';SESSIONS_DIR.mkdir(parents=_B,exist_ok=_B);A=SESSIONS_DIR/persona_id;A.mkdir(parents=_B,exist_ok=_B);return A/f"{session_id}.json"
def create_session_id():'生成新的会话 ID（供无 session_id 时新建会话）。';return uuid.uuid4().hex
def load_history(persona_id:str,session_id:str):
	'\n    按 persona_id + session_id 从存储加载历史，返回供 run_agent_loop 使用的 messages：\n    [ {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ... ]\n    会话不存在或读取出错时返回空列表。\n    ';B=_session_path(persona_id,session_id)
	if not B.is_file():return[]
	E=B.read_text(encoding=_F);F=json.loads(E);G=F.get(_C)or[];C=[]
	for A in G:
		H=A.get(_G,_K);D=(A.get(_D)or A.get(_L)or'').strip()
		if D:C.append({_G:H,_D:D})
	return C
def append_turn(persona_id:str,session_id:str,user_input:str,reply:str,*,step_contents:list|_A=_A,link:str|_A=_A,ui_schema:dict|_A=_A,thinking_content:str|_A=_A):
	'\n    追加一轮对话到会话文件。若文件不存在则新建；若存在则追加一条 user + 一条 assistant 记录。\n    assistant 条会保存 step_contents（步骤名、耗时、内容、input、prompt）、thinking_content（思考过程，可选）。\n    ';J='created_at';I='persona_id';G=user_input;D=thinking_content;C=session_id;B=persona_id;E=_session_path(B,C);K=datetime.now(timezone.utc).isoformat();L=datetime.now(timezone.utc).isoformat()
	if E.is_file():
		M=E.read_text(encoding=_F)
		try:A=json.loads(M)
		except Exception:A={_M:C,I:B,_C:[]}
	else:A={_M:C,I:B,_C:[]}
	A[_J]=K;F=A.get(_C)or[];N=step_contents or[];F.append({_G:_K,_D:G,_L:G,J:L});O=datetime.now(timezone.utc).isoformat();H={_G:'assistant',_D:reply,'step_contents':N,'link':link,_H:ui_schema,J:O}
	if D and D.strip():H['thinking_content']=D.strip()
	F.append(H);A[_C]=F;E.write_text(json.dumps(A,ensure_ascii=_E,indent=2),encoding=_F)
def list_sessions(persona_id:str):
	'\n    列出当前分身下的所有会话，按修改时间倒序。\n    返回 [ {"session_id", "updated_at", "preview"}, ... ]，session_id 不含 .json 后缀。\n    ';D=SESSIONS_DIR/persona_id
	if not D.is_dir():return[]
	A=[]
	for E in D.glob('*.json'):
		G=E.stem
		try:H=E.read_text(encoding=_F);B=json.loads(H)
		except Exception:B={}
		I=B.get(_J)or'';J=B.get(_C)or[];F=''
		for C in J:
			if C.get(_G)==_K:F=(C.get(_D)or C.get(_L)or'')[:80].strip();break
		A.append({_M:G,_J:I,'preview':F or'(无预览)'})
	A.sort(key=lambda x:x.get(_J)or'',reverse=_B);return A
def delete_session(persona_id:str,session_id:str):
	'\n    删除指定会话文件。若文件存在并删除成功返回 True，否则返回 False。\n    ';A=_session_path(persona_id,session_id)
	if not A.is_file():return _E
	try:A.unlink();return _B
	except Exception:return _E
def start_timing_session():'开始新一轮计时会话（通常在收到用户输入时调用），清空并记录起点。';global _timing_session;A=time.time();_timing_session=[('start',A,_A,_A,_A)]
def record_step(step_name:str,content:Any=_A,input_sent:Any=_A,prompt_sent:Any=_A):
	'\n    记录当前时刻为一个步骤节点（由流程在路由、每轮 API、工具调用等处调用）。\n\n    @param step_name 步骤标识，如 "router"、"agent_start"、"final_reply"\n    @param content 该步骤的返回内容，如 router 选中的 agent_id、工具结果、最终回复等\n    @param input_sent 该步骤的简短传入摘要（如工具名+参数），用于步骤明细展示\n    @param prompt_sent 该步骤发送给 AI 的完整 prompt（本步调用模型时的 messages 可读串），用于步骤明细「发送内容」\n    ';global _timing_session
	if _timing_session is _A:start_timing_session()
	_timing_session.append((step_name,time.time(),content,input_sent,prompt_sent))
def get_step_contents():
	'\n    返回当前请求各步骤的名称、耗时、内容与传入内容，用于会话 step_contents 与前端展示。\n    prompt 写在「上一步」中，表示触发本步的完整发送内容；不记录 input。\n    若第一步（无上一步）有 prompt，则单独返回供调用方写入预置的 user_input 步。\n\n    @return (steps, prompt_for_first_step)，steps 为列表；prompt_for_first_step 仅当第一步有 prompt 时非空\n    '
	if not _timing_session or len(_timing_session)<2:return[],_A
	A=[];D=_A
	for E in range(1,len(_timing_session)):
		B=_timing_session[E];F=B[0];G=B[1];H=B[2];C=B[4]if len(B)>4 else _A;I=round(G-_timing_session[E-1][1],3);J={'step':F,'duration':f"{I}",_D:H};A.append(J)
		if len(A)>=2 and C is not _A:A[-2]['prompt']=C
		elif C is not _A and len(A)==1:D=C
	return A,D
def get_timing_data():
	'\n    返回当前请求各步骤的 (步骤名, 距起点秒数, 距上一步秒数)。\n    无会话时返回空列表。\n    '
	if not _timing_session or len(_timing_session)<2:return[]
	D=_timing_session[0][1];B=[]
	for A in range(1,len(_timing_session)):E,C=_timing_session[A][0],_timing_session[A][1];F=round(C-D,3);G=round(C-_timing_session[A-1][1],3);B.append((E,F,G))
	return B
def get_and_clear_next_open_url():
	'\n    读取 open_url 技能写入的 URL；若存在则返回并删除文件，供 ChatResponse.link 使用。\n    @return URL 或 None\n    '
	if not NEXT_OPEN_URL_PATH.exists():return
	try:B=json.loads(NEXT_OPEN_URL_PATH.read_text(encoding=_F));A=(B.get('url')or'').strip();NEXT_OPEN_URL_PATH.unlink(missing_ok=_B);return A if A else _A
	except Exception:NEXT_OPEN_URL_PATH.unlink(missing_ok=_B);return
def get_timing_report():
	'\n    获取当前请求的计时报告：从用户输入到获得结果的每一步耗时。\n    包含各步骤名称、距起点时间、本步耗时（秒），便于分析延迟与性能。\n    ';A=get_timing_data()
	if not A:return'暂无计时数据（尚未开始或未记录任何步骤）。'
	B=[]
	for(C,F,D)in A:B.append(f"{C}\n{D}")
	E=A[-1][1]if A else 0;B.append(f"总耗时\n{E} 秒");return'\n\n'.join(B)
def extract_ui_schema_payload(reply:str):
	'\n    从回复文本中提取 ui_schema。\n    使用 JSF（JSON Schema Form）风格：\n    1) JSON 中包含 ui_schema / uiSchema 字段\n    2) 直接给出 JSON Schema 对象本体（type=object 且含 properties）\n    @param reply 助手回复文本\n    @return 规范化后的 ui_schema（dict）或 None\n    ';A=(reply or'').strip()
	if not A:return
	B=[];D=re.findall(_N,A,flags=re.IGNORECASE);B.extend(D);B.append(A)
	for E in B:
		C=_parse_ui_schema_candidate(E)
		if C is not _A:return C
def strip_ui_schema_from_reply(reply:str):
	'\n    从回复文本中移除 uiSchema 相关 JSON 内容，避免直接展示/存储在 reply 字段。\n    若移除后文本为空且检测到 uiSchema，则返回一条简短提示文本。\n    ';A=reply or'';B=_E
	def C(match):
		A=match;nonlocal B;C=A.group(1);D=_parse_ui_schema_candidate(C)
		if D is not _A:B=_B;return''
		return A.group(0)
	A=re.sub(_N,C,A,flags=re.IGNORECASE);A=A.strip()
	if A:
		D=_parse_ui_schema_candidate(A)
		if D is not _A:B=_B;A=''
	if not A.strip()and B:return'已生成 UI 表单，请在弹窗中继续交互。'
	return A.strip()
def _parse_ui_schema_candidate(candidate:str):
	'尝试解析单个 JSON 候选并抽取 JSF 风格 ui_schema。';E=candidate;D='uiSchema';C='schema'
	if not E:return
	try:A=json.loads(E)
	except Exception:return
	if not isinstance(A,dict):return
	if isinstance(A.get(_H),dict):return A[_H]
	if isinstance(A.get(D),dict):return A[D]
	if isinstance(A.get(C),dict)and _looks_like_jsf_schema(A[C]):return A[C]
	if isinstance(A.get(_I),dict):
		B=A[_I]
		if isinstance(B.get(_H),dict):return B[_H]
		if isinstance(B.get(D),dict):return B[D]
		if isinstance(B.get(C),dict)and _looks_like_jsf_schema(B[C]):return B[C]
	if _looks_like_jsf_schema(A):return A
def _looks_like_jsf_schema(obj:dict):
	'粗略判断对象是否像 JSON Schema：type=object 且含 properties。';A=obj
	if not isinstance(A,dict):return _E
	if A.get('type')!='object':return _E
	return isinstance(A.get('properties'),dict)