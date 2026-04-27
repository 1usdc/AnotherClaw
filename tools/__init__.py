'\nAgent 可用工具包：技能通过 read_file + exec_bash 执行，不由后端 subprocess 直接跑。\n流程：技能发现 → 技能过滤 → 技能 prompt 注入 → 系统提示 → Session → LLM 调用 → read_file 读 SKILL.md、exec_bash 执行。\n'
from utils.skill import SKILLS_ROOT,search_skills_by_keyword
from.file_tools import exec_bash,read_file,write_file
from.skill_tools import list_skill_tree,search_skills
from utils.session import get_step_contents,record_step,start_timing_session
TOOLS=[read_file,write_file,exec_bash,list_skill_tree,search_skills]
tool_map={A.name:A for A in TOOLS}
__all__=['TOOLS','tool_map','read_file','write_file','exec_bash','list_skill_tree','search_skills','search_skills_by_keyword','get_step_contents','start_timing_session','record_step','SKILLS_ROOT']