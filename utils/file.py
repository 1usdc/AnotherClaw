'\n项目内路径解析、exec 策略与虚拟环境 PATH：供 ``tools.file_tools`` 中 LLM 可调工具复用。\n'
_T='错误: path 不能为空。'
_S='/workspace/.pydeps'
_R='python3.'
_Q='php'
_P='java'
_O='node'
_N='python3'
_M='/workspace'
_L='VIRTUAL_ENV'
_K='.venv'
_J='PATH'
_I='pip3'
_H='uv'
_G='python'
_F='podman'
_E='pip'
_D='|'
_C=False
_B=None
_A=True
import logging,os,shlex,subprocess
from pathlib import Path
_BASE_DIR=Path(__file__).resolve().parents[1]
SAFE_EXEC_ROOT=str(_BASE_DIR)
PROJECT_ROOT=str(_BASE_DIR)
DEFAULT_TIMEOUT=30
MAX_TIMEOUT=120
PODMAN_IMAGE_PYTHON=os.getenv('ANOTHERCLAW_PODMAN_IMAGE_PYTHON','docker.io/library/python:3.12')
PODMAN_IMAGE_NODE=os.getenv('ANOTHERCLAW_PODMAN_IMAGE_NODE','docker.io/library/node:22')
PODMAN_IMAGE_SHELL=os.getenv('ANOTHERCLAW_PODMAN_IMAGE_SHELL','docker.io/library/bash:5.2')
PODMAN_IMAGE_GO=os.getenv('ANOTHERCLAW_PODMAN_IMAGE_GO','docker.io/library/golang:1.22')
PODMAN_IMAGE_JAVA=os.getenv('ANOTHERCLAW_PODMAN_IMAGE_JAVA','docker.io/library/openjdk:21-jdk')
PODMAN_IMAGE_RUST=os.getenv('ANOTHERCLAW_PODMAN_IMAGE_RUST','docker.io/library/rust:latest')
PODMAN_IMAGE_PHP=os.getenv('ANOTHERCLAW_PODMAN_IMAGE_PHP','docker.io/library/php:8.3-cli')
PODMAN_IMAGE_DEFAULT=os.getenv('ANOTHERCLAW_PODMAN_IMAGE',PODMAN_IMAGE_SHELL)
DEFAULT_BLOCKED_TOKEN_PATTERNS='||',';','>','<','$(','`'
DEFAULT_BLOCKED_COMMAND_KEYWORDS='rm','mv','cp','chmod','chown','sudo','shutdown','reboot','mkfs','dd','kill','pkill','killall'
logger=logging.getLogger('anotherclaw.utils.file')
def ensure_podman_ready(timeout:int):
	'\n    确认可用 podman；macOS 下自动启动（必要时初始化）podman machine。\n    ';H='already running';G='machine';D=max(1,min(int(timeout),MAX_TIMEOUT))
	try:E=subprocess.run([_F,'--version'],capture_output=_A,text=_A,timeout=D,shell=_C)
	except FileNotFoundError:return'错误: 未找到 podman。请先执行 just start 安装 podman。'
	except subprocess.TimeoutExpired:return'错误: 检测 podman 超时。'
	if E.returncode!=0:A=(E.stderr or E.stdout or'').strip();B=f": {A}"if A else'';return f"错误: podman 不可用{B}"
	if os.name=='posix'and'darwin'in os.uname().sysname.lower():
		try:I=subprocess.run([_F,G,'inspect'],capture_output=_A,text=_A,timeout=D,shell=_C)
		except subprocess.TimeoutExpired:return'错误: 检测 podman machine 超时。'
		if I.returncode!=0:
			F=subprocess.run([_F,G,'init'],capture_output=_A,text=_A,timeout=D,shell=_C)
			if F.returncode!=0:A=(F.stderr or F.stdout or'').strip();B=f": {A}"if A else'';return f"错误: podman machine init 失败{B}"
		C=subprocess.run([_F,G,'start'],capture_output=_A,text=_A,timeout=D,shell=_C)
		if C.returncode!=0:
			J=(C.stderr or'').lower();K=(C.stdout or'').lower()
			if H not in J and H not in K:A=(C.stderr or C.stdout or'').strip();B=f": {A}"if A else'';return f"错误: podman machine 启动失败{B}"
	return''
def ensure_podman_image_ready(image:str,timeout:int):
	'\n    确保目标镜像已在本地可用；若不存在先执行 pull。\n    首次拉取通常慢于业务命令执行，使用更宽松的超时窗口。\n    ';C=timeout;A=image;G=max(1,min(int(C),MAX_TIMEOUT))
	try:H=subprocess.run([_F,'image','exists',A],capture_output=_A,text=_A,timeout=G,shell=_C)
	except subprocess.TimeoutExpired:return f"错误: 检查镜像超时: {A}"
	except Exception as D:return f"错误: 检查镜像失败: {D}"
	if H.returncode==0:return''
	E=max(180,min(max(C*3,C),600))
	try:B=subprocess.run([_F,'pull',A],capture_output=_A,text=_A,timeout=E,shell=_C)
	except subprocess.TimeoutExpired:return f"错误: 拉取镜像超时（{E} 秒）: {A}"
	except Exception as D:return f"错误: 拉取镜像失败: {D}"
	if B.returncode!=0:F=(B.stderr or B.stdout or'').strip();I=f": {F}"if F else'';return f"错误: 拉取镜像失败（exit {B.returncode}）{I}"
	return''
def _container_workdir(cwd:str):
	'仅挂载工作目录时，容器内工作目录固定为 /workspace。';A=os.path.realpath(cwd)
	if os.path.isdir(A):return _M
	return _M
def _resolve_skill_mount_dir(cwd:str):
	'\n    限制容器仅挂载 ``skills/`` 下目录，避免暴露整个项目目录。\n    返回 (mount_dir, error_message)。\n    ';B=cwd
	try:A=os.path.realpath(B)
	except OSError:return _B,f"错误: 无法解析工作目录: {B}"
	C=os.path.realpath(os.path.join(SAFE_EXEC_ROOT,'skills'))
	if not(A==C or A.startswith(C+os.sep)):return _B,'错误: 仅允许执行 skills 目录内命令，请设置 working_dir=skills/<skill-name>。'
	if not os.path.isdir(A):return _B,f"错误: working_dir 不存在: {B}"
	return A,''
def _detect_runtime(cmd_text:str):
	'\n    基于命令文本推断运行时类型：python/node/shell/go/java/rust/php/default。\n    对单管道命令优先参考右侧可执行文件（例如 curl ... | sh）。\n    ';B=cmd_text;C=[B]
	if _D in B and B.count(_D)==1:C=[A.strip()for A in B.split(_D,1)if A.strip()]
	D=[]
	for F in C:
		try:E=shlex.split(F)
		except ValueError:continue
		if not E:continue
		D.append(os.path.basename(E[0]).lower())
	G={_G,_N,_E,_I,_H,'pytest','poetry'};H={_O,'npm','npx','pnpm','yarn','bun','deno'};I={'sh','bash','zsh','dash','ash'};J={'go','gofmt'};K={_P,'javac','mvn','mvnw','gradle','gradlew'};L={'cargo','rustc','rustup'};M={_Q,'composer'}
	for A in reversed(D):
		if A in G:return _G
		if A in H:return _O
		if A in I:return'shell'
		if A in J:return'go'
		if A in K:return _P
		if A in L:return'rust'
		if A in M:return _Q
	return'default'
def select_podman_image(cmd_text:str):
	'根据命令推断运行时并选择对应镜像。';A=_detect_runtime(cmd_text)
	if A==_G:return PODMAN_IMAGE_PYTHON
	if A==_O:return PODMAN_IMAGE_NODE
	if A=='shell':return PODMAN_IMAGE_SHELL
	if A=='go':return PODMAN_IMAGE_GO
	if A==_P:return PODMAN_IMAGE_JAVA
	if A=='rust':return PODMAN_IMAGE_RUST
	if A==_Q:return PODMAN_IMAGE_PHP
	return PODMAN_IMAGE_DEFAULT
def _podman_env_args(env:dict[str,str]):
	'将环境变量转成 podman --env 参数，过滤宿主机路径相关变量。';C={_J,_L,'PWD','OLDPWD','SHLVL','_'};A=[]
	for(B,D)in env.items():
		if B in C:continue
		A.extend(['--env',f"{B}={D}"])
	return A
def normalize_command_for_container(cmd_text:str,mount_dir:str):
	'\n    将命令中的宿主机挂载目录路径归一化为容器路径 /workspace。\n    兼容历史技能中遗留的宿主机绝对路径写法。\n    ';A=cmd_text;B=os.path.realpath(mount_dir).replace('\\','/')
	if not B:return A
	return A.replace(B,_M)
def load_exec_policy():
	'\n    从 SQLite config 表（key=command_whitelist）读取执行策略：仅黑名单（禁止的符号、禁止的命令名）。\n    不存在或格式异常时使用内置默认值。\n    ';E=tuple(DEFAULT_BLOCKED_TOKEN_PATTERNS);F=tuple(DEFAULT_BLOCKED_COMMAND_KEYWORDS);C=DEFAULT_TIMEOUT;D=MAX_TIMEOUT
	try:from utils.db import CONFIG_KEY_COMMAND_WHITELIST as K,db_get_config as L;A=L(K)
	except Exception:A=_B
	if isinstance(A,dict):
		G=A.get('blocked_token_patterns')
		if isinstance(G,list):
			B=tuple(str(A)for A in G if str(A))
			if B:E=B
		H=A.get('blocked_command_keywords')
		if isinstance(H,list):
			B=tuple(str(A).strip()for A in H if str(A).strip())
			if B:F=B
		I=A.get('default_timeout');J=A.get('max_timeout')
		if isinstance(I,int):C=max(1,I)
		if isinstance(J,int):D=max(1,J)
		if C>D:C=D
	return E,F,C,D
def venv_executable_dir(venv_root:Path):
	'\n    若 ``venv_root`` 为有效虚拟环境目录，返回其可执行目录（Unix 为 ``bin``，Windows 为 ``Scripts``）。\n    ';A=venv_root
	if not A.is_dir():return
	if os.name=='nt':B=A/'Scripts';return str(B)if B.is_dir()else _B
	C=A/'bin';return str(C)if C.is_dir()else _B
def project_venv_bin_dir():'\n    若项目根存在 ``.venv``，返回其可执行目录。\n    供 ``exec_bash`` 将 ``uv`` 等解析到与后端一致的虚拟环境；技能子目录另有 ``cwd/.venv``。\n    ';return venv_executable_dir(Path(SAFE_EXEC_ROOT)/_K)
def exec_env_with_project_venv(base:dict[str,str]):
	'\n    在 ``base`` 上为 ``PATH`` 前置项目 ``.venv`` 的 bin，并设置 ``VIRTUAL_ENV``（若目录存在）。\n    ';B=project_venv_bin_dir()
	if not B:return base
	A=dict(base);C=A.get(_J,'')or'';A[_J]=os.pathsep.join([B,C])if C else B;A[_L]=str(Path(SAFE_EXEC_ROOT)/_K);return A
def is_project_root_cwd(cwd:str):
	'是否为 exec 根目录（未指定 ``working_dir`` 时的 cwd）。'
	try:return os.path.realpath(cwd)==os.path.realpath(SAFE_EXEC_ROOT)
	except OSError:return _C
def ensure_uv_venv_in_dir(cwd:str,env:dict[str,str],timeout:int):
	'\n    在 ``cwd`` 下若尚无可用 ``.venv``，则执行 ``uv venv`` 创建。\n    @returns 失败时的错误文案；成功返回 None。\n    ';B=Path(cwd)/_K
	if venv_executable_dir(B):return
	D=max(1,min(int(timeout),MAX_TIMEOUT))
	try:A=subprocess.run([_H,'venv'],cwd=cwd,env=env,capture_output=_A,text=_A,timeout=D,shell=_C)
	except FileNotFoundError:return'错误: 未找到 uv。请安装 uv（https://github.com/astral-sh/uv）或确保项目根 .venv 的 Scripts|bin 在 PATH 中。'
	except subprocess.TimeoutExpired:return'错误: uv venv 创建虚拟环境超时。'
	if A.returncode!=0:C=(A.stderr or A.stdout or'').strip();E=f": {C}"if C else'';return f"错误: uv venv 失败（exit {A.returncode}）{E}"
	if not venv_executable_dir(B):return'错误: uv venv 已执行但 .venv 未就绪。'
def exec_env_with_skill_and_project_venv(cwd:str,base:dict[str,str]):
	'\n    ``PATH`` 顺序：``cwd/.venv``（若存在）、项目 ``.venv``、原有 PATH（便于技能环境优先、且仍能解析 ``uv``）。\n    ``VIRTUAL_ENV`` 优先指向 ``cwd/.venv``，否则项目 ``.venv``。\n    ';A=dict(base);E=Path(cwd)/_K;B=venv_executable_dir(E);C=project_venv_bin_dir();D=[]
	if B:D.append(B)
	if C and C!=B:D.append(C)
	if D:F=A.get(_J,'')or'';G=os.pathsep.join(D);A[_J]=os.pathsep.join([G,F])if F else G
	if B:A[_L]=str(E.resolve())
	elif C:A[_L]=str(Path(SAFE_EXEC_ROOT)/_K)
	return A
def rewrite_python_command_to_uv(cmd_text:str):
	'\n    在技能工作目录下将 ``pip`` / ``python`` 类命令改写为 ``uv pip`` / ``uv run``；含管道时不改写。\n    Windows 下引号规则复杂，跳过改写。\n    ';B=cmd_text
	if os.name=='nt'or _D in B:return B
	try:A=shlex.split(B,posix=_A)
	except ValueError:return B
	if not A:return B
	D=A[0];C=os.path.basename(D)
	if C.startswith(_G)and len(A)>=3 and A[1]=='-m'and A[2]in(_E,_I):return shlex.join([_H,_E,*A[3:]])
	if C in(_E,_I):return shlex.join([_H,_E,*A[1:]])
	if C==_G or C==_N or len(C)>7 and C.startswith(_R):return shlex.join([_H,'run',D,*A[1:]])
	return B
def rewrite_pip_install_to_workspace_target(cmd_text:str):
	'\n    在容器 ``--rm`` 场景下，将 ``pip install`` 自动落到挂载目录：\n    ``--target /workspace/.pydeps``。\n    若用户已显式指定 target/prefix/root/user，则保持原命令不改写。\n    含管道命令不改写。\n    ';G='--target';F='install';B=cmd_text
	if _D in B:return B
	try:A=shlex.split(B,posix=_A)
	except ValueError:return B
	if not A:return B
	C=os.path.basename(A[0]).lower();D=-1
	if C in(_E,_I)and len(A)>=2 and A[1]==F:D=2
	elif(C==_G or C==_N or len(C)>7 and C.startswith(_R))and len(A)>=4 and A[1]=='-m'and A[2]in(_E,_I)and A[3]==F:D=4
	elif C==_H and len(A)>=3 and A[1]==_E and A[2]==F:D=3
	if D<0:return B
	E=set(A[D:])
	if G in E or'-t'in E or'--prefix'in E or'--root'in E or'--user'in E:return B
	return shlex.join([*A,G,_S])
def _inject_workspace_pythonpath(env:dict[str,str],mount_dir:str):
	'\n    若挂载目录存在 ``.pydeps``，自动注入 ``PYTHONPATH=/workspace/.pydeps``，\n    以便后续 ``python`` 直接可见 ``pip --target`` 安装的依赖。\n    ';E='PYTHONPATH';F=os.path.join(mount_dir,'.pydeps')
	if not os.path.isdir(F):return env
	A=dict(env);B=_S;D=(A.get(E)or'').strip();C=[A for A in D.split(os.pathsep)if A]if D else[]
	if B not in C:A[E]=os.pathsep.join([B,*C])if C else B
	return A
def resolve_read_path(path:str):
	'\n    解析读文件路径：支持相对项目根的路径，且必须落在项目根内。\n    返回 (resolved_abs_path, error_message)；成功时 error_message 为空。\n    ';B=path
	if not B or not B.strip():return _B,_T
	C=B.strip().replace('\\',os.sep)
	if os.path.isabs(C):A=os.path.normpath(C)
	else:A=os.path.normpath(os.path.join(PROJECT_ROOT,C))
	try:A=os.path.realpath(A)
	except OSError:return _B,f"错误: 路径无法解析: {B}"
	D=os.path.realpath(PROJECT_ROOT)
	if not(A==D or A.startswith(D+os.sep)):return _B,f"错误: 路径必须在项目根内: {B}"
	if not os.path.isfile(A):return _B,f"错误: 不是文件或不存在: {B}"
	return A,''
def resolve_write_path(path:str):
	'\n    解析写文件路径：支持相对项目根的路径，且必须落在项目根内；目标可为新文件，父目录不存在则创建。\n    返回 (resolved_abs_path, error_message)；成功时 error_message 为空。\n    ';B=path
	if not B or not B.strip():return _B,_T
	C=B.strip().replace('\\',os.sep);D=os.path.realpath(PROJECT_ROOT)
	if os.path.isabs(C):A=os.path.normpath(C)
	else:A=os.path.normpath(os.path.join(PROJECT_ROOT,C))
	if os.path.exists(A):
		try:A=os.path.realpath(A)
		except OSError:pass
		if os.path.isdir(A):return _B,f"错误: 路径是目录而非文件: {B}"
	else:A=os.path.abspath(A)
	if not(A==D or A.startswith(D+os.sep)):return _B,f"错误: 路径必须在项目根内: {B}"
	return A,''
def run_shell_command(cmd_text:str,*,cwd:str,timeout:int,env:dict[str,str],blocked_command_keywords:tuple[str,...]):
	'\n    在黑名单校验通过后执行命令；支持单管道 shell 或 argv 列表。\n    返回 stdout 成功摘要，或非零 exit / 超时的错误说明字符串。\n    ';R='错误: 管道两侧不能为空。';H=blocked_command_keywords;D=timeout;A=cmd_text;S=_D in A
	if S:
		if A.count(_D)!=1:return'错误: 仅支持单管道命令（如 curl -sSL url | sh），不支持多管道。'
		T=[A.strip()for A in A.split(_D,1)]
		for I in T:
			if not I:return R
			try:
				J=shlex.split(I)
				if not J:return R
				C=os.path.basename(J[0])
				if C in H:return f"错误: 禁止执行危险命令: {C}"
			except ValueError:return'错误: 命令解析失败。'
	else:
		K=shlex.split(A)
		if not K:return'错误: command 不能为空。'
		C=os.path.basename(K[0])
		if C in H:return f"错误: 禁止执行危险命令: {C}"
	L=ensure_podman_ready(D)
	if L:return L
	B,M=_resolve_skill_mount_dir(cwd)
	if M or B is _B:return M or'错误: 无法解析技能目录。'
	U=_container_workdir(B);G=select_podman_image(A);N=ensure_podman_image_ready(G,D)
	if N:return N
	E=normalize_command_for_container(A,B);E=rewrite_pip_install_to_workspace_target(E);O=_inject_workspace_pythonpath(env,B);P=[_F,'run','--rm','-i','-v',f"{B}:/workspace",'-w',U,*_podman_env_args(O),G,'sh','-lc',E];logger.info('run_shell_command executing | cwd=%s | image=%s | cmd_raw=%s | cmd_exec=%s | podman=%s',B,G,A,E,shlex.join(P))
	try:
		F=subprocess.run(P,capture_output=_A,text=_A,timeout=D,cwd=B,shell=_C,env=O);Q=F.stdout or'';V=F.stderr or''
		if F.returncode!=0:return f"exit code: {F.returncode}\nstdout:\n{Q}\nstderr:\n{V}"
		return Q.strip()or'(no output)'
	except subprocess.TimeoutExpired:return f"错误: 命令超时（{D} 秒）"
	except Exception as W:return f"错误: {W}"