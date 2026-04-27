'\n文件与 shell 工具：读文件、执行 bash 命令（实现层在 ``utils.file``）。\n'
_B='错误: 无法解析路径。'
_A='文件路径（相对项目根或绝对路径，须在项目内）'
import os
from typing import Annotated
from dotenv import dotenv_values
from langchain_core.tools import tool
from utils.skill import merge_env_with_skill_dotenv
from utils.file import DEFAULT_TIMEOUT,SAFE_EXEC_ROOT,exec_env_with_project_venv,load_exec_policy,resolve_read_path,resolve_write_path,run_shell_command
@tool(description='读取项目内指定路径的文本文件内容；路径可为相对项目根，如 skills/技能名/SKILL.md。')
def read_file(path:Annotated[str,_A]):
	'读取项目内指定路径的文本文件内容。路径相对项目根时如 skills/weather/SKILL.md。';A,B=resolve_read_path(path)
	if B or A is None:return B or _B
	with open(A,'r',encoding='utf-8',errors='replace')as C:return C.read()
@tool(description='向项目内指定路径写入文本内容；路径可为相对项目根，如 skills/技能名/SKILL.md；父目录不存在会自动创建。')
def write_file(path:Annotated[str,_A],content:Annotated[str,'要写入的完整文本内容']):
	'向项目内指定路径写入文本内容。路径相对项目根时如 skills/weather/SKILL.md。';A,C=resolve_write_path(path)
	if C or A is None:return C or _B
	try:
		B=os.path.dirname(A)
		if B and not os.path.isdir(B):os.makedirs(B,exist_ok=True)
		with open(A,'w',encoding='utf-8')as D:D.write(content)
		return'已写入: '+path
	except OSError as E:return f"错误: 写入失败: {E}"
@tool(description='在技能目录执行一条命令（仅黑名单限制：禁止多管道/重定向等符号与危险命令）。容器仅挂载 working_dir 指向的 skills/xxx 目录并以 /workspace 为工作目录；{baseDir} 会替换为容器路径 /workspace。')
def exec_bash(command:Annotated[str,'要执行的命令（可含 {baseDir}；支持单管道如 curl -sSL url | sh；禁止 ;、>、< 等与黑名单命令）'],working_dir:Annotated[str,'技能工作目录（建议必填，需在 skills/ 下，如 skills/crypto-price）']='',timeout_sec:Annotated[int,'超时时间（秒，默认 30，最大 120）']=DEFAULT_TIMEOUT):
	'执行一条命令；仅黑名单限制，command 中的 {baseDir} 会替换为容器内路径 /workspace。';L='{baseDir}';H=timeout_sec;E=command;A=working_dir;M,N,O,P=load_exec_policy()
	if not E or not E.strip():return'错误: command 不能为空。'
	B=E.strip()
	if any(A in B for A in M):return'错误: 不允许使用管道、重定向、命令拼接或命令替换符号。'
	F=H if isinstance(H,int)else O;F=max(1,min(F,P));G=SAFE_EXEC_ROOT
	if A and A.strip():
		C=os.path.realpath(os.path.join(SAFE_EXEC_ROOT,A));I=os.path.realpath(SAFE_EXEC_ROOT)
		if not C.startswith(I+os.sep)and C!=I:return'错误: working_dir 必须在项目目录内。'
		if not os.path.isdir(C):return f"错误: working_dir 不存在: {A}"
		G=C
	if L in B:
		if not A or not A.strip():return'错误: 使用 {baseDir} 时必须提供技能目录 working_dir（如 skills/crypto-price）。'
		Q=A.strip().replace('\\','/').strip('/')
		if not Q.startswith('skills/'):return'错误: 使用 {baseDir} 时，working_dir 必须是 skills/ 下的技能目录。'
		B=B.replace(L,'/workspace')
	D=dict(os.environ);J=os.path.join(SAFE_EXEC_ROOT,'.env')
	if os.path.isfile(J):
		for K in dotenv_values(J).keys():
			if K:D.pop(str(K),None)
	D=merge_env_with_skill_dotenv(G,base=D);R=exec_env_with_project_venv(D);return run_shell_command(B,cwd=G,timeout=F,env=R,blocked_command_keywords=N)