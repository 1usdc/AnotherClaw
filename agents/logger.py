'\nAgent 日志工具：控制台 + 按天写入 data/logs，保留 60 天，供各模块导入使用。\n\n使用示例:\n    from agents.logger import get_logger\n    logger = get_logger(__name__)\n    logger.info("消息")\n'
_B=True
_A=None
import datetime,logging
from pathlib import Path
_AGENTS_DIR=Path(__file__).resolve().parent
_BASE_DIR=_AGENTS_DIR.parent
LOG_DIR=_BASE_DIR/'data'/'logs'
LOG_DIR.mkdir(parents=_B,exist_ok=_B)
DEFAULT_LOG_BASE_NAME='agent'
BACKUP_DAYS=60
APP_LOGGER_NAME='anotherclaw'
class DailyFileHandler(logging.Handler):
	'\n    按天创建日志文件，文件名为 {base_name}_{YYYY-MM-DD}.log；\n    在切换到新的一天时删除超过 backup_days 的旧文件。\n    '
	def __init__(A,log_dir:Path,base_name:str=DEFAULT_LOG_BASE_NAME,backup_days:int=BACKUP_DAYS,encoding:str='utf-8'):super().__init__();A._log_dir=Path(log_dir);A._log_dir.mkdir(parents=_B,exist_ok=_B);A._base_name=base_name;A._backup_days=backup_days;A._encoding=encoding;A._current_date=_A;A._stream=_A;A.terminator='\n'
	def _path_for(A,d:datetime.date):return A._log_dir/f"{A._base_name}_{d:%Y-%m-%d}.log"
	def _open_today(A):
		B=datetime.date.today()
		if A._current_date==B and A._stream is not _A:return
		A.close_stream();A._current_date=B;C=A._path_for(B);A._stream=open(C,'a',encoding=A._encoding);A._purge_old()
	def _purge_old(A):
		D=datetime.date.today()-datetime.timedelta(days=A._backup_days)
		for B in A._log_dir.glob(f"{A._base_name}_*.log"):
			try:
				C=B.stem
				if'_'not in C:continue
				E=C.split('_',1)[1];F=datetime.datetime.strptime(E,'%Y-%m-%d').date()
				if F<D:B.unlink()
			except(ValueError,OSError):pass
	def close_stream(A):
		if A._stream is not _A:
			try:A._stream.close()
			except OSError:pass
			A._stream=_A
	def emit(A,record:logging.LogRecord):
		B=record
		try:
			A._open_today();C=A.format(B)
			if A._stream:A._stream.write(C+A.terminator);A._stream.flush()
		except Exception:A.handleError(B)
	def close(A):A.close_stream();super().close()
def _build_handlers():'创建控制台与按天文件的 Handler。';C=logging.Formatter('%(asctime)s | %(levelname)-7s | %(name)s | %(message)s',datefmt='%Y-%m-%d %H:%M:%S');A=logging.StreamHandler();A.setLevel(logging.DEBUG);A.setFormatter(C);B=DailyFileHandler(log_dir=LOG_DIR,base_name=DEFAULT_LOG_BASE_NAME,backup_days=BACKUP_DAYS);B.setLevel(logging.INFO);B.setFormatter(C);return A,B
_app_logger=logging.getLogger(APP_LOGGER_NAME)
if not _app_logger.handlers:_app_logger.setLevel(logging.DEBUG);_app_logger.propagate=False;_console,_file=_build_handlers();_app_logger.addHandler(_console);_app_logger.addHandler(_file)
def get_logger(name:str):
	'\n    获取具名 logger，挂在应用 logger 下（anotherclaw.*），不使用 root logger。\n\n    @param {string} name - 通常使用 __name__\n    @returns {logging.Logger}\n    ';A=(name or'').strip()
	if not A:return _app_logger
	if A==APP_LOGGER_NAME or A.startswith(APP_LOGGER_NAME+'.'):return logging.getLogger(A)
	return logging.getLogger(f"{APP_LOGGER_NAME}.{A}")