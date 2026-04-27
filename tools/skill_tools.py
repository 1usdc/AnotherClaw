'\nAgent 可调技能工具：列出/检索技能（实现见 ``utils.skill``）。\n'
from typing import Annotated
from langchain_core.tools import tool
from utils.skill import list_skill_tree_text,search_skills_by_keyword
@tool(description='列出技能树：skills/ 下各技能目录及描述（来自 SKILL.md frontmatter），便于根据描述用 read_file(location) + exec_bash 执行。')
def list_skill_tree():'\n    列出技能树：从内存中的 frontmatter 缓存读取各技能名称与描述。\n    返回可读列表（技能名: 描述），便于用 read_file(skills/技能名/SKILL.md) 查看、exec_bash 执行。\n    ';return list_skill_tree_text()
@tool(description='按关键词检索本地技能，返回匹配的技能列表（格式同 list_skill_tree）；用户表达意图后先调用此工具缩小候选，再用 read_file(path) + exec_bash 执行。')
def search_skills(query:Annotated[str,'检索关键词，支持多词（空格分隔）；匹配技能名、描述或 keywords']):'\n    按关键词检索本地技能，返回匹配的技能列表（格式同 list_skill_tree）。\n    用户表达意图后先调用此工具缩小候选，再用 read_file(skills/技能名/SKILL.md) 查看、exec_bash 执行。\n    ';return search_skills_by_keyword(query)