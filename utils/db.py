'\nSQLite 数据层：数据库存于 data/database/sqlite.db。\n分身元数据为文件存储（见 utils.memory：memory/<id>/_meta.json）；skill_ratings / config 等在本库。\nconfig 表：command_whitelist 等为 JSON 文本；全局环境变量（大写 KEY）为纯文本，由 db_env_* 读写。\n'
_S='INSERT INTO skill_ratings (skill_key, data) VALUES (?, ?)'
_R='INSERT INTO trusted_devices (id, user_agent, fingerprint, note, created_at) VALUES (?, ?, ?, ?, ?)'
_Q='fingerprint'
_P='user_agent'
_O='updated_at'
_N='next_run_at'
_M='status'
_L='prompt'
_K='interval_seconds'
_J='start_time'
_I='INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)'
_H='SELECT value FROM config WHERE key = ?'
_G='created_at'
_F='data'
_E=True
_D='value'
_C=False
_B='skill_key'
_A=None
import json,os,sqlite3
from pathlib import Path
from typing import Any
BASE_DIR=Path(__file__).resolve().parents[1]
DATA_DIR=BASE_DIR/_F
DB_DIR=DATA_DIR/'database'
DB_PATH=DB_DIR/'sqlite.db'
def _ensure_data_dir():DATA_DIR.mkdir(parents=_E,exist_ok=_E);DB_DIR.mkdir(parents=_E,exist_ok=_E)
def get_connection():'获取可读写的 SQLite 连接；自动创建 data/database 目录与数据库文件。';_ensure_data_dir();A=sqlite3.connect(str(DB_PATH),check_same_thread=_C);A.row_factory=sqlite3.Row;return A
def _migrate_trusted_devices_to_ua_fingerprint(conn:sqlite3.Connection):
	"\n    若表为仅 fingerprint 唯一（旧版），则重建为 (user_agent, fingerprint) 联合唯一；\n    旧数据写入 ``user_agent=''``（须重新登记带真实 UA 的记录，或保留仅指纹匹配见业务约定）。\n    ";A=conn
	try:
		D=A.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='trusted_devices'").fetchone()
		if not D:return
		E={A[1]for A in A.execute('PRAGMA table_info(trusted_devices)').fetchall()}
		if _P in E:return
		F=A.row_factory;A.row_factory=sqlite3.Row;G=A.execute('SELECT id, fingerprint, note, created_at FROM trusted_devices ORDER BY created_at DESC').fetchall();A.row_factory=F;A.execute('DROP TABLE trusted_devices');A.executescript('\n            CREATE TABLE trusted_devices (\n                id TEXT PRIMARY KEY,\n                user_agent TEXT NOT NULL,\n                fingerprint TEXT NOT NULL,\n                note TEXT,\n                created_at TEXT NOT NULL,\n                UNIQUE(user_agent, fingerprint)\n            );\n            ')
		for B in G:
			C=(B[_Q]or'').strip()
			if not C:continue
			A.execute(_R,(B['id'],'',C,B['note']or'',B[_G]))
		A.commit()
	except Exception:A.rollback();raise
def init_schema(conn:sqlite3.Connection):'创建表结构（若不存在）。记忆存于 data/memory/ 文件，不在此库。';A=conn;A.executescript("\n        CREATE TABLE IF NOT EXISTS skill_ratings (\n            skill_key TEXT PRIMARY KEY,\n            data TEXT NOT NULL\n        );\n        CREATE TABLE IF NOT EXISTS config (\n            key TEXT PRIMARY KEY,\n            value TEXT NOT NULL\n        );\n        CREATE TABLE IF NOT EXISTS scheduled_tasks (\n            id TEXT PRIMARY KEY,\n            start_time TEXT NOT NULL,\n            interval_seconds INTEGER NOT NULL,\n            prompt TEXT NOT NULL,\n            status TEXT NOT NULL DEFAULT 'active',\n            next_run_at TEXT,\n            created_at TEXT NOT NULL,\n            updated_at TEXT NOT NULL\n        );\n        CREATE TABLE IF NOT EXISTS trusted_devices (\n            id TEXT PRIMARY KEY,\n            user_agent TEXT NOT NULL,\n            fingerprint TEXT NOT NULL,\n            note TEXT,\n            created_at TEXT NOT NULL,\n            UNIQUE(user_agent, fingerprint)\n        );\n    ");A.commit();_migrate_trusted_devices_to_ua_fingerprint(A)
def _conn():'获取连接并确保 schema 已初始化。';A=get_connection();init_schema(A);return A
def db_load_skill_ratings():
	'从 SQLite 加载评分列表，格式与原 JSON 一致：[{ skill_key, count?, ... }, ...]。';B=_conn()
	try:
		E=B.execute('SELECT skill_key, data FROM skill_ratings').fetchall();C=[]
		for A in E:
			D=json.loads(A[_F])if A[_F]else{}
			if isinstance(D,dict):C.append({_B:A[_B],**D})
		return C
	finally:B.close()
def db_save_skill_ratings(items:list[dict[str,Any]]):
	'将评分列表写入 SQLite；每项需含 skill_key，其余字段存为 JSON。';A=_conn()
	try:
		A.execute('DELETE FROM skill_ratings')
		for B in items:
			if not isinstance(B,dict)or not B.get(_B):continue
			C=B[_B];D={A:B for(A,B)in B.items()if A!=_B};A.execute(_S,(C,json.dumps(D,ensure_ascii=_C)))
		A.commit()
	finally:A.close()
def db_remove_skill_rating(skill_key:str):
	'从评分表删除指定 skill_key；返回是否删除。';A=_conn()
	try:B=A.execute('DELETE FROM skill_ratings WHERE skill_key = ?',[skill_key]);A.commit();return B.rowcount>0
	finally:A.close()
CONFIG_KEY_COMMAND_WHITELIST='command_whitelist'
def db_get_config(key:str):
	'读取 config 表；返回 JSON 解析后的 dict，不存在返回 None。';B=_conn()
	try:
		A=B.execute(_H,[key]).fetchone()
		if not A or not A[_D]:return
		return json.loads(A[_D])
	finally:B.close()
def db_set_config(key:str,value:dict[str,Any]):
	'写入 config 表（JSON 序列化）。';A=_conn()
	try:A.execute(_I,(key,json.dumps(value,ensure_ascii=_C)));A.commit()
	finally:A.close()
def db_env_get(key:str):
	'从 config 读取一条全局环境变量；不存在返回 None（与空字符串区分：空串仍会返回 ""）。';A=key;A=(A or'').strip()
	if not A:return
	B=_conn()
	try:
		C=B.execute(_H,(A,)).fetchone()
		if not C:return
		D=C[_D];return D if D is not _A else''
	finally:B.close()
def db_env_set(key:str,value:str):
	'写入或更新 config 中的全局环境变量。';A=key;A=(A or'').strip();B=_conn()
	try:B.execute(_I,(A,value));B.commit()
	finally:B.close()
def db_env_apply_all_to_environ():
	'将 config 中所有合法大写环境变量键同步到 os.environ（覆盖同名键）。';from utils.skill import is_valid_env_key as D;B=_conn()
	try:
		E=B.execute('SELECT key, value FROM config').fetchall()
		for A in E:
			C=A['key']
			if not D(C):continue
			os.environ[C]=A[_D]if A[_D]is not _A else''
	finally:B.close()
def db_list_scheduled_tasks():
	'列出所有定时任务，按创建时间倒序。';A=_conn()
	try:B=A.execute('SELECT id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at FROM scheduled_tasks ORDER BY created_at DESC').fetchall();return[dict(A)for A in B]
	finally:A.close()
def db_get_scheduled_task(task_id:str):
	'按 id 获取一条定时任务。';A=_conn()
	try:B=A.execute('SELECT id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at FROM scheduled_tasks WHERE id = ?',(task_id,)).fetchone();return dict(B)if B else _A
	finally:A.close()
def db_create_scheduled_task(rec:dict[str,Any]):
	'创建定时任务。rec 需含 id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at。';A=rec;B=_conn()
	try:B.execute('INSERT INTO scheduled_tasks (id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',(A['id'],A[_J],A[_K],A[_L],A.get(_M,'active'),A.get(_N),A[_G],A[_O]));B.commit()
	finally:B.close()
def db_update_scheduled_task(task_id:str,*,start_time:str|_A=_A,interval_seconds:int|_A=_A,prompt:str|_A=_A,status:str|_A=_A,next_run_at:str|_A=_A,updated_at:str):
	'更新定时任务；仅传要改的字段。返回是否找到。';H=next_run_at;G=status;F=prompt;E=interval_seconds;D=start_time;C=task_id;B=_conn()
	try:
		A=B.execute('SELECT * FROM scheduled_tasks WHERE id = ?',(C,)).fetchone()
		if not A:return _C
		A=dict(A)
		if D is not _A:A[_J]=D
		if E is not _A:A[_K]=E
		if F is not _A:A[_L]=F
		if G is not _A:A[_M]=G
		if H is not _A:A[_N]=H
		A[_O]=updated_at;B.execute('UPDATE scheduled_tasks SET start_time=?, interval_seconds=?, prompt=?, status=?, next_run_at=?, updated_at=? WHERE id=?',(A[_J],A[_K],A[_L],A[_M],A[_N],A[_O],C));B.commit();return _E
	finally:B.close()
def db_delete_scheduled_task(task_id:str):
	'删除定时任务。返回是否找到并删除。';A=_conn()
	try:B=A.execute('DELETE FROM scheduled_tasks WHERE id = ?',(task_id,));A.commit();return B.rowcount>0
	finally:A.close()
def db_get_tasks_due(next_run_before:str):
	"获取 next_run_at <= next_run_before 且 status='active' 的任务，用于调度执行。";A=_conn()
	try:B=A.execute("SELECT id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at FROM scheduled_tasks WHERE status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= ?",(next_run_before,)).fetchall();return[dict(A)for A in B]
	finally:A.close()
def db_trusted_device_pair_exists(user_agent:str,fingerprint:str):
	'是否存在相同的 user_agent + fingerprint 登记。';A=_conn()
	try:B=A.execute('SELECT 1 FROM trusted_devices WHERE user_agent = ? AND fingerprint = ? LIMIT 1',(user_agent,fingerprint)).fetchone();return B is not _A
	finally:A.close()
def db_trusted_device_list():
	'列出所有已登记设备。';A=_conn()
	try:B=A.execute('SELECT id, user_agent, fingerprint, note, created_at FROM trusted_devices ORDER BY created_at DESC').fetchall();return[dict(A)for A in B]
	finally:A.close()
def db_trusted_device_insert(rec:dict[str,Any]):
	'插入一条登记。rec 需含 id, user_agent, fingerprint, note, created_at。';A=rec;B=_conn()
	try:B.execute(_R,(A['id'],A[_P],A[_Q],A.get('note')or'',A[_G]));B.commit()
	finally:B.close()
def db_trusted_device_delete(device_id:str):
	'按 id 删除。返回是否删除成功。';A=_conn()
	try:B=A.execute('DELETE FROM trusted_devices WHERE id = ?',(device_id,));A.commit();return B.rowcount>0
	finally:A.close()
def db_trusted_device_count():
	'已登记设备数量。';A=_conn()
	try:B=A.execute('SELECT COUNT(*) FROM trusted_devices').fetchone();return int(B[0])if B else 0
	finally:A.close()
def migrate_from_json_if_needed():
	'若 SQLite 表为空且对应 JSON 文件存在，则从 JSON 导入数据。';F='utf-8';A=get_connection();init_schema(A)
	try:
		G=A.execute('SELECT COUNT(*) FROM skill_ratings').fetchone()[0]
		if G==0:
			B=DATA_DIR/'skill_ratings.json'
			if B.is_file():
				try:
					C=json.loads(B.read_text(encoding=F))
					if isinstance(C,list):
						for D in C:
							if isinstance(D,dict)and D.get(_B):H=D[_B];I={A:B for(A,B)in D.items()if A!=_B};A.execute(_S,(H,json.dumps(I,ensure_ascii=_C)))
						A.commit()
				except Exception:pass
		E=A.execute(_H,[CONFIG_KEY_COMMAND_WHITELIST]).fetchone()
		if not E or not E[_D]:
			B=DATA_DIR/'command_whitelist.json'
			if B.is_file():
				try:
					C=json.loads(B.read_text(encoding=F))
					if isinstance(C,dict):A.execute(_I,(CONFIG_KEY_COMMAND_WHITELIST,json.dumps(C,ensure_ascii=_C)));A.commit()
				except Exception:pass
	finally:A.close()