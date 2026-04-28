'\nAgent 共享逻辑与默认实现：消息转 API 格式、OpenAI 兼容 API、工具循环及默认 Agent（直连 API、技能检索注入）。\n'
_Y='thinking'
_X='\n\n## 更早的对话摘要\n'
_W='assistant'
_V='description'
_U='OPENAI_API_KEY'
_T='N1N_API_KEY'
_S='delta'
_R='choices'
_Q='（无）'
_P='arguments'
_O='...'
_N='tool_calls'
_M='system'
_L='function'
_K='args'
_J='final_reply'
_I=True
_H='id'
_G='\n\n'
_F='user'
_E='name'
_D='role'
_C=False
_B='content'
_A=None
import json,os
from pathlib import Path
from typing import Any,Callable,List,Optional
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage,ToolMessage
from openai import OpenAI
from agents.logger import get_logger
from tools import TOOLS,record_step,tool_map
from utils.memory import format_memories_for_prompt
from utils.prompt import get_agent_system_prompt_for_persona
from utils.session import extract_ui_schema_payload,strip_ui_schema_from_reply
from utils.skill import get_skill_summaries_for_agent,search_skills_by_keyword
_logger=get_logger(__name__)
def tools_openai():'工具定义转为 OpenAI function 格式。';return[{'type':_L,_L:{_E:A.name,_V:A.description or'','parameters':A.get_input_schema().model_json_schema()}}for A in TOOLS]
def _format_messages_for_step_log(messages:list,max_chars:int|_A=4000,max_tool_content:int|_A=500):
	'\n    将消息列表格式化为可读字符串，用于步骤明细中「传给 AI 的内容」展示或写入。\n    max_chars 为 None 时不截断总长度；max_tool_content 为 None 时不截断 tool 内容（写入会话时用完整数据）。\n    ';G=max_tool_content;F=max_chars;D=[];H=0
	for A in messages:
		if isinstance(A,SystemMessage):E,B=_M,A.content or''
		elif isinstance(A,HumanMessage):E,B=_F,A.content or''
		elif isinstance(A,AIMessage):
			E,B=_W,A.content or''
			if getattr(A,_N,_A):B+=' [tool_calls: '+', '.join((A.get(_E)or'?')+'('+json.dumps(A.get(_K)or{},ensure_ascii=_C)+')'for A in A.tool_calls)+']'
		elif isinstance(A,ToolMessage):
			I=A.content or''
			if G is not _A and len(I)>G:B=I[:G]+_O
			else:B=I
			E='tool'
		else:continue
		C=f"[{E}]\n{B}"
		if F is not _A and H+len(C)>F:C=C[:F-H]+'\n...';D.append(C);break
		D.append(C);H+=len(C)
	return _G.join(D)if D else''
def messages_to_openai(messages:list):
	'LangChain messages -> OpenAI API messages。';B=[]
	for A in messages:
		if isinstance(A,SystemMessage):B.append({_D:_M,_B:A.content})
		elif isinstance(A,HumanMessage):B.append({_D:_F,_B:A.content})
		elif isinstance(A,AIMessage):
			C={_D:_W,_B:A.content or''}
			if getattr(A,_N,_A):C[_N]=[{_H:A.get(_H,''),'type':_L,_L:{_E:A.get(_E,''),_P:json.dumps(A.get(_K)or{})}}for A in A.tool_calls]
			B.append(C)
		elif isinstance(A,ToolMessage):B.append({_D:'tool','tool_call_id':A.tool_call_id,_B:A.content})
	return B
def _safe_json_loads(raw:str):
	'安全解析 JSON 字符串，失败时返回空字典。'
	if not raw:return{}
	try:A=json.loads(raw);return A if isinstance(A,dict)else{}
	except Exception:return{}
def analyze_conversation_for_memory(client:OpenAI,model:str,user_input:str,reply:str,max_summary_chars:int=500):
	'\n    判断本轮对话是否包含与用户相关的、值得长期记忆的信息；若值得则生成简短总结。\n    返回 (是否应写入记忆, 总结文本)；若不值得或出错则返回 (False, "")。\n    ';H='STORE';A=(user_input or'').strip();B=(reply or'').strip()
	if not A and not B:return _C,''
	I=A[:800]+('…'if len(A)>800 else'');J=B[:1200]+('…'if len(B)>1200 else'');K='你是记忆分析助手。根据「用户消息」与「助手回复」，判断是否包含与用户本人相关的、值得长期记住的信息。\n值得存储的示例：用户的偏好、决定、承诺、个人事实、待办、重要约定、明确说「记住」的内容等。\n不值得存储的示例：纯闲聊、一次性问答、工具执行结果无用户上下文、寒暄、无关紧要的确认。\n若不值得存储，只回复一行：NO_STORE\n若值得存储，先回复一行：STORE\n然后空一行，再写一段简短中文总结（一两句话，不超过 200 字），不要重复用户/助手原文。';L=f"用户消息：\n{I}\n\n助手回复：\n{J}"
	try:
		M=client.chat.completions.create(model=model,messages=[{_D:_M,_B:K},{_D:_F,_B:L}],temperature=.2,max_tokens=400);C=(M.choices[0].message.content or'').strip()
		if not C:return _C,''
		E=C.upper()
		if E.startswith('NO_STORE'):return _C,''
		if E.startswith(H):
			N=C.split('\n');F=[]
			for(O,D)in enumerate(N):
				if O==0 and D.strip().upper()==H:continue
				if D.strip():F.append(D.strip())
			G=' '.join(F).strip()
			if G:return _I,G[:max_summary_chars]
		return _C,''
	except Exception:return _C,''
def summarize_conversation(client:OpenAI,model:str,messages_list:List[dict],max_summary_chars:int=1500):
	'\n    将较早的对话交给模型做摘要，返回一条紧凑的摘要文本。\n    messages_list 为 [{"role": "user"|"assistant", "content": str}, ...]。\n    ';C=messages_list
	if not C:return''
	A=[]
	for D in C:
		F=(D.get(_D)or _F).lower();B=(D.get(_B)or'').strip()
		if not B:continue
		G='用户'if F==_F else'助手';A.append(f"{G}：{B[:800]}"+('…'if len(B)>800 else''))
	if not A:return''
	H='请用一段简短的中文概括以下对话的主要话题、用户诉求与关键结论（控制在 300 字内）：\n\n'+_G.join(A)
	try:I=client.chat.completions.create(model=model,messages=[{_D:_F,_B:H}],temperature=.3,max_tokens=500);E=(I.choices[0].message.content or'').strip();return E[:max_summary_chars]if E else''
	except Exception:return'（摘要生成失败，已省略更早对话）'
def _history_to_langchain(history:List[dict]):
	'将 [{"role":"user"|"assistant","content":str}, ...] 转为 LangChain 消息列表。';A=[]
	for B in history:
		D=(B.get(_D)or _F).lower();C=B.get(_B)or''
		if D==_F:A.append(HumanMessage(content=C))
		else:A.append(AIMessage(content=C))
	return A
def _prune_old_tool_results(messages:list,keep_recent:int=3,max_chars_per_old:int=800):
	'\n    仅裁切较早的 ToolMessage 内容以减轻 context 体积，不改对话本身。\n    保留最近 keep_recent 条工具结果完整，更早的截断到 max_chars_per_old 字符。\n    原地修改 messages。\n    ';D=max_chars_per_old;C=keep_recent;A=messages;E=[A for(A,B)in enumerate(A)if isinstance(B,ToolMessage)]
	if len(E)<=C:return
	H=E[:-C]
	for F in H:
		B=A[F]
		if not isinstance(B,ToolMessage):continue
		G=B.content or''
		if len(G)<=D:continue
		A[F]=ToolMessage(content=G[:D]+'\n\n…（结果已截断，仅保留最近若干条完整）',tool_call_id=B.tool_call_id)
def chat_with_tools(client:OpenAI,model:str,messages:list,temperature:float=0,on_text_delta:Optional[Callable[[str],_A]]=_A,on_thinking_delta:Optional[Callable[[str],_A]]=_A):
	'调用 OpenAI 兼容 API（stream=True），返回 AIMessage（含 content 与 tool_calls）。思考已在外部先执行并注入 messages，此处仅流式输出回复。';J=on_text_delta;P=client.chat.completions.create(model=model,messages=messages_to_openai(messages),tools=tools_openai(),temperature=temperature,stream=_I);K=[];B={}
	for Q in P:
		L=getattr(Q,_R,_A)or[]
		if not L:continue
		C=getattr(L[0],_S,_A)
		if not C:continue
		D=getattr(C,_B,_A)
		if D:
			K.append(D)
			if J:J(D)
		R=getattr(C,_N,_A)or[]
		for E in R:
			A=getattr(E,'index',0)or 0;F=B.setdefault(A,{_H:'',_E:'',_P:''});M=getattr(E,_H,_A)
			if M:F[_H]=M
			G=getattr(E,_L,_A)
			if G:
				N=getattr(G,_E,_A)
				if N:F[_E]+=N
				O=getattr(G,_P,_A)
				if O:F[_P]+=O
	H=[]
	for A in sorted(B.keys()):I=B[A];H.append({_H:I[_H]or f"call_{A}",_E:I[_E],_K:_safe_json_loads(I[_P])})
	return AIMessage(content=''.join(K),tool_calls=H if H else[])
NEED_SKILLS_PROMPT='你只需判断：以下用户输入是否必须通过「使用工具」才能完成？\n工具包括：读文件、写文件、执行命令、列出/检索技能、创建或执行技能，查询特定网页信息、数字货币的查询与交易、polymarket的查询与交易。\n若仅需普通对话回答则不需要工具，例如：问候、常识、闲聊、解释概念、生活类问答\n仅回复一个词：YES 或 NO, 难以判断默认回复 NO。'
SIMPLE_CHAT_SYSTEM_PROMPT='你是友好、简洁的助手，直接回答用户问题。无需使用任何工具或技能。'
THINK_ONLY_INSTRUCTION='【本回合】你只需输出你的思考过程（推理、计划、可选方案），不要输出最终回答。你的思考将作为下一轮调用的上下文。'
EXECUTE_WITH_THINKING_APPEND='\n\n## 你刚才的思考\n{thinking}\n\n请根据上述思考直接给出最终回复，不要重复思考内容。'
def _call_think_phase(client:OpenAI,model:str,messages:list,on_thinking_delta:Optional[Callable[[str],_A]]=_A,temperature:float=.3):
	'\n    先思考阶段：在现有 messages 上追加「仅输出思考」指令，流式返回思考内容并回调 on_thinking_delta，返回完整思考文本。\n    不传 tools，仅一次 completion。\n    ';C=on_thinking_delta;A=messages
	if not A or not isinstance(A[0],SystemMessage):return''
	G=(A[0].content or'')+_G+THINK_ONLY_INSTRUCTION;H=[SystemMessage(content=G)]+list(A[1:]);I=messages_to_openai(H);D=[]
	try:
		J=client.chat.completions.create(model=model,messages=I,temperature=temperature,stream=_I)
		for K in J:
			E=getattr(K,_R,_A)or[]
			if not E:continue
			F=getattr(E[0],_S,_A)
			if not F:continue
			B=getattr(F,_B,_A)
			if B:
				D.append(B)
				if C:C(B)
	except Exception:return''
	return''.join(D).strip()
def _is_obviously_simple_chat(raw:str):
	'\n    明显属于简单对话（问候、天气、短追问等）则返回 True，不调用路由模型。\n    用于避免路由模型误判导致答非所问。\n    ';B=raw
	if not B or len(B)>60:return _C
	A=B.strip()
	if not A:return _C
	if len(A)<=25 and any(B in A for B in('天气','你好','谢谢','嗨','早','晚','怎么样','呢','吗','啊')):return _I
	if A in('你好','您好','hi','hello','谢谢','感谢'):return _I
	return _C
def _need_skills(client:OpenAI,model:str,user_input:str):
	'\n    判断用户输入是否需要使用技能/工具才能完成。\n    返回 True 表示需要走 Agent 工具循环，False 表示直接一次大模型回复即可。\n    ';A=(user_input or'').strip()
	if not A:_logger.info('_need_skills: 输入为空 -> 简单答复');return _C
	if _is_obviously_simple_chat(A):_logger.info('_need_skills: 明显简单对话 -> 简单答复 | 用户输入: %s',A[:80]+(_O if len(A)>80 else''));return _C
	try:
		C=client.chat.completions.create(model=model,messages=[{_D:_M,_B:NEED_SKILLS_PROMPT},{_D:_F,_B:A[:2000]}],temperature=0,max_tokens=10);B=(C.choices[0].message.content or'').strip().upper()
		if'NO'in B or'否'in B:_logger.info('_need_skills: 模型回复 %r -> 简单答复 | 用户输入: %s',B,A[:80]+(_O if len(A)>80 else''));return _C
		_logger.info('_need_skills: 模型回复 %r -> 使用技能/工具 | 用户输入: %s',B,A[:80]+(_O if len(A)>80 else''));return _I
	except Exception as D:_logger.warning('_need_skills: 判断请求异常 %s -> 使用技能/工具（降级） | 用户输入: %s',D,A[:80]+(_O if len(A)>80 else''));return _I
def _chat_simple(client:OpenAI,model:str,user_input:str,history_prefix:Optional[List[dict]]=_A,summary_before_history:Optional[str]=_A,on_step:Optional[Callable[[str,Any],_A]]=_A,on_text_delta:Optional[Callable[[str],_A]]=_A,on_thinking_delta:Optional[Callable[[str],_A]]=_A,persona_prompt_prefix:str=''):
	'\n    不使用工具：先思考阶段流式输出思考，再将思考注入提示词执行一次大模型得到回复。\n    支持历史上下文与流式 on_thinking_delta（思考）、on_text_delta（回答）、on_step。\n    persona_prompt_prefix 为分身提示词，会拼在 system 前。\n    ';M=on_text_delta;L=on_step;K=user_input;J=model;I=client;F=persona_prompt_prefix;E=summary_before_history;B=history_prefix;A=SIMPLE_CHAT_SYSTEM_PROMPT
	if F and F.strip():A=F.strip()+_G+A
	if E and E.strip():A=A+_X+E.strip()
	C=[SystemMessage(content=A)]
	if B:C.extend(_history_to_langchain(B))
	C.append(HumanMessage(content=K));N=_call_think_phase(I,J,C,on_thinking_delta=on_thinking_delta,temperature=.3);S=_format_messages_for_step_log(C,max_chars=_A,max_tool_content=_A);record_step(_Y,N or _Q,input_sent='(think_only)',prompt_sent=S);T=A+EXECUTE_WITH_THINKING_APPEND.format(thinking=N or _Q);D=[SystemMessage(content=T)]
	if B:D.extend(_history_to_langchain(B))
	D.append(HumanMessage(content=K));U=messages_to_openai(D);O=[]
	try:
		V=I.chat.completions.create(model=J,messages=U,temperature=.3,stream=_I)
		for W in V:
			P=getattr(W,_R,_A)or[]
			if not P:continue
			Q=getattr(P[0],_S,_A)
			if not Q:continue
			G=getattr(Q,_B,_A)
			if G:
				O.append(G)
				if M:M(G)
	except Exception as X:return f"回复生成失败：{X}"
	H=''.join(O).strip()or'(无回复)';R=_format_messages_for_step_log(D,max_chars=_A,max_tool_content=_A);record_step(_J,H,input_sent=R,prompt_sent=R)
	if L:L(_J,H)
	return H
def _format_tool_calls_for_step_log(tool_calls:list):
	'\n    将本轮模型返回的 tool_calls 格式化为可读文本（含 JSON 参数），\n    便于在 llm_response 步骤中展示如 exec_bash 的实际命令等。\n    ';B=tool_calls
	if not B:return''
	C=[]
	for D in B:
		F=(D or{}).get(_E,'?');A=(D or{}).get(_K);G=A if isinstance(A,dict)else{}
		try:E=json.dumps(G,ensure_ascii=_C)
		except Exception:E=str(A)
		C.append(f"{F}({E})")
	return'\n'.join(C)
def _run_agent_loop_core(client:OpenAI,model:str,system_prompt:str,user_input:str,max_turns:int=12,history_prefix:Optional[List[dict]]=_A,summary_before_history:Optional[str]=_A,on_step:Optional[Callable[[str,Any],_A]]=_A,on_text_delta:Optional[Callable[[str],_A]]=_A,on_thinking_delta:Optional[Callable[[str],_A]]=_A,request_ui_schema:Optional[Callable[[dict],dict|_A]]=_A):
	'\n    OpenClaw 风格 Agent 循环：多轮调用 API、执行工具直到无 tool_calls 或达 max_turns。\n\n    @param history_prefix 当前对话中最近若干条 [{"role","content"}]，拼在 system 与当前 user 之间\n    @param summary_before_history 更早对话的摘要，会追加到 system_prompt 后\n    @param on_step 可选；每记录一步时回调 (step_name, content)，用于推送步骤\n    @param on_text_delta 可选；收到模型文本增量时回调 (text_piece)，用于真正流式文本\n    @param on_thinking_delta 可选；收到模型思考增量时回调 (text_piece)，用于流式展示思考过程\n    ';d='ui_schema_submit';W=request_ui_schema;V=history_prefix;U=model;T=client;S='(max turns reached)';N=on_text_delta;M=summary_before_history;C=on_step;K=system_prompt
	if M and M.strip():K=K+_X+M.strip()
	A=[SystemMessage(content=K)]
	if V:A.extend(_history_to_langchain(V))
	A.append(HumanMessage(content=user_input));F=0;O=0
	while F<max_turns:
		_prune_old_tool_results(A,keep_recent=3,max_chars_per_old=800);e=A[O:];D=_format_messages_for_step_log(e,max_chars=_A,max_tool_content=_A);X=_call_think_phase(T,U,A,on_thinking_delta=on_thinking_delta,temperature=0);record_step(_Y,X or _Q,input_sent=f"turn={F+1}",prompt_sent=D);f=K+EXECUTE_WITH_THINKING_APPEND.format(thinking=X or _Q);g=[SystemMessage(content=f)]+list(A[1:]);G=chat_with_tools(T,U,g,on_text_delta=N,on_thinking_delta=_A);E=getattr(G,_N,_A)or[];Y=G.content or'';Z=extract_ui_schema_payload(Y)
		if Z is not _A:
			H=strip_ui_schema_from_reply(Y)
			if W is _A:G=AIMessage(content=H,tool_calls=E if E else[])
			else:
				if H and N:N(H)
				a=W(Z)
				if a is _A:
					B=(H or'').strip()or'参数表单未提交，流程已终止。';record_step(_J,B,input_sent=D,prompt_sent=D)
					if C:C(_J,B)
					return B
				A.append(AIMessage(content=H or'请填写参数后继续执行。'));P=json.dumps(a,ensure_ascii=_C);A.append(HumanMessage(content=f"用户已提交参数(JSON)：{P}\n请继续执行后续步骤。"));record_step(d,P,input_sent='ui_schema',prompt_sent=D)
				if C:C(d,P)
				O=len(A);F+=1;continue
		if E:h=_format_tool_calls_for_step_log(E);record_step('llm_response',h,input_sent=f"turn={F+1}",prompt_sent=D)
		if not E:
			B=(G.content or'').strip()or'(no reply)';record_step(_J,B,input_sent=D,prompt_sent=D)
			if C:C(_J,B)
			return B
		A.append(G)
		for L in E:
			I=L.get(_E,'');b=L.get(_K)if isinstance(L.get(_K),dict)else{};i=L.get(_H,'');c=I;j=I+'('+json.dumps(b,ensure_ascii=_C)+')'
			if I in tool_map:
				try:Q=tool_map[I].invoke(b);J=Q if isinstance(Q,str)else str(Q)
				except Exception as k:J=f"Error: {k}"
			else:J=f"Unknown tool: {I}"
			A.append(ToolMessage(content=J,tool_call_id=i));record_step(c,J,input_sent=j,prompt_sent=D)
			if C:C(c,J)
		O=len(A);F+=1
	B=S
	for R in reversed(A):
		if isinstance(R,AIMessage)and getattr(R,_B,_A):B=(R.content or'').strip()or S;break
	record_step(_J,B,input_sent=S,prompt_sent='')
	if C:C(_J,B)
	return B
def _get_client():'按当前环境变量创建 OpenAI 客户端。';A=os.getenv(_T)or os.getenv(_U)or'';B=os.getenv('OPENAI_BASE_URL','https://api.n1n.ai/v1');return OpenAI(api_key=A,base_url=B)
def _get_model():return os.getenv('OPENAI_MODEL','gpt-4o')
def optimize_task_prompt_text(raw:str):
	'\n    将定时任务提示词草稿润色为更清晰、可执行的版本（单次补全，不跑工具）。\n    未配置 API 密钥时抛出 ValueError。\n    ';A=(raw or'').strip()
	if not A:return''
	if not(os.getenv(_T)or os.getenv(_U)or'').strip():raise ValueError('尚未配置 API 密钥，无法优化提示词')
	C=_get_client();D=_get_model();E='你是助手。用户会写一条在「定时触发」时发给自动化 Agent 的提示词草稿。\n请改写为：目标明确、上下文足够、尽量可一步执行；保留用户意图与关键约束；不要加引号、标题或「以下是优化后」等前言，只输出最终提示词正文。';F=C.chat.completions.create(model=D,messages=[{_D:_M,_B:E},{_D:_F,_B:A[:8000]}],temperature=.3,max_tokens=2048);B=(F.choices[0].message.content or'').strip();return B if B else A
STRENGTHS='通用对话、工具调用'
KEEP_RECENT_MESSAGES=10
def _persona_prompt_prefix(persona_id:str|_A):
	'从 agents/prompts/{persona_id}.md 读取分身提示词，作为 system 前缀；无则返回空串。';A=persona_id
	if not(A or'').strip():return''
	try:from utils.prompt import get_persona_system_prompt as B;C=B(A.strip());return(C or'').strip()
	except Exception:return''
def _persona_prompt_with_memories(persona_id:str|_A):
	'\n    分身系统提示词 + 记忆页长期记忆（data/memory/{persona_id}/），供拼入 system。\n    ';C=persona_id;A=_persona_prompt_prefix(C)
	try:B=format_memories_for_prompt(C)
	except Exception as E:_logger.warning('format_memories_for_prompt failed: %s',E);return A
	if not B.strip():return A
	D='## 用户长期记忆（来自记忆库，回答时可自然参考，勿机械罗列除非用户问起）'
	if A.strip():return A.strip()+_G+D+_G+B.strip()
	return D+_G+B.strip()
def run_agent_loop(user_input:str,max_turns:int=12,history=_A,on_step=_A,on_text_delta=_A,on_thinking_delta=_A,persona_id:str|_A=_A,request_ui_schema:Optional[Callable[[dict],dict|_A]]=_A):
	'\n    默认 Agent 入口：先判断用户输入是否需要使用技能；不需要则直接请求一次大模型回答，\n    需要则按用户意图做技能检索注入系统提示并执行工具循环。\n    persona_id 有值时，从 agents/prompts/{persona_id}.md 加载分身提示词，并注入 data/memory 下长期记忆，拼到 system 前。\n    ';P=persona_id;O=on_thinking_delta;N=on_text_delta;M=on_step;C=user_input;A=history
	if not(os.getenv(_T)or os.getenv(_U)or'').strip():return'尚未配置 API 密钥。请在右上角「设置」页保存 OPENAI_API_KEY。'
	D=_get_client();E=_get_model();H=_persona_prompt_with_memories(P);F=_A;I=_A
	if A and len(A)>0:
		if len(A)>KEEP_RECENT_MESSAGES:I=summarize_conversation(D,E,A[:-KEEP_RECENT_MESSAGES]);F=A[-KEEP_RECENT_MESSAGES:]
		else:F=A
	if not _need_skills(D,E,C or''):return _chat_simple(client=D,model=E,user_input=C or'',history_prefix=F,summary_before_history=I,on_step=M,on_text_delta=N,on_thinking_delta=O,persona_prompt_prefix=H)
	Q=get_agent_system_prompt_for_persona(P);R=get_skill_summaries_for_agent()
	if R:
		J=['\n## 已加载技能（用 read_file(path) 读 SKILL.md，再按文档用 exec_bash 执行）\n']
		for K in R:
			L=K.get(_E)or'';S=K.get('location')or f"skills/{L}/SKILL.md";T=(K.get(_V)or'').strip()[:200]
			if T:J.append(f"- {L}  path: {S}  — {T}")
			else:J.append(f"- {L}  path: {S}")
		B=Q+'\n'.join(J)
	else:B=Q
	if H:B=H.strip()+_G+B
	G=search_skills_by_keyword(C or'')
	if G and G.strip()and'当前无技能'not in G:B=B+'\n\n与当前用户意图相关的技能（可优先选用）：\n'+G
	return _run_agent_loop_core(client=D,model=E,system_prompt=B,user_input=C,max_turns=max_turns,history_prefix=F,summary_before_history=I,on_step=M,on_text_delta=N,on_thinking_delta=O,request_ui_schema=request_ui_schema)
def analyze_for_memory(user_input:str,reply:str):'判断对话是否包含与用户相关的信息并生成总结，供写入记忆前调用。';return analyze_conversation_for_memory(_get_client(),_get_model(),user_input or'',reply or'')