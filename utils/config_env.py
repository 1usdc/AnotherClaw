'\n应用全局配置：自 SQLite ``config`` 表读写环境变量，启动时可选从遗留 ``.env`` 一次性导入。\n'
from pathlib import Path
from dotenv import dotenv_values
from utils.db import db_env_apply_all_to_environ,db_env_get,db_env_set,migrate_from_json_if_needed
from utils.skill import is_valid_env_key
def migrate_dotenv_file_to_config(base_dir:Path):
	'\n    若应用根目录存在 ``.env``，将其中的大写环境变量导入 ``config`` 表（仅当该键在库中尚不存在时写入）。\n    不删除 ``.env`` 文件；此后新配置仅写入数据库。\n    ';B=Path(base_dir).resolve()/'.env'
	if not B.is_file():return
	try:D=dotenv_values(B)
	except OSError:return
	for(A,C)in D.items():
		if not A or not is_valid_env_key(A):continue
		if C is None:continue
		if db_env_get(A)is not None:continue
		db_env_set(A,str(C))
def init_app_environment(base_dir:Path):'初始化存储、从旧 JSON/``.env`` 迁移，并将库中环境变量同步到 ``os.environ``。';migrate_from_json_if_needed();migrate_dotenv_file_to_config(base_dir);db_env_apply_all_to_environ()