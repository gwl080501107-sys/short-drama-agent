"""
W1 —— 手写一个 Agent Loop（不要用框架）

【现在项目的模式】
    用户请求 -> 你写死的步骤 -> 一次 LLM 调用 -> 返回
    这是 workflow，步骤是你决定的。

【Agent 的模式】
    用户请求 -> [模型决策 -> 调工具 -> 结果回传 -> 模型再决策] ... -> 返回
    这是 loop，走几步、调什么工具，是模型决定的。

【W1 的验收标准】
    不看文档，能讲清这三件事：
    1. 循环什么时候停？为什么是这三个终止条件而不是别的？
    2. 工具执行抛异常了，为什么不直接崩，要返回给模型？
    3. 模型给的 arguments 是 JSON 字符串，解析失败怎么办？

运行方式：
    .venv/bin/python -m app.agent_loop
"""

import json
import logging
import re
import sys

from app.llm_client import client

logger = logging.getLogger(__name__)

MODEL = "deepseek-flash"
MAX_STEPS = 8


# ---------------------------------------------------------------------------
# 一、工具实现
#
# 注意：工具必须返回「给模型看的字符串」，不是 Python 对象。
# 返回 JSON 字符串是为了让模型能结构化地理解结果。
# ---------------------------------------------------------------------------

def count_episodes(outline: str) -> str:
    """统计分集大纲的集数，并检查是否从第 1 集连续编号。"""
    numbers = [int(n) for n in re.findall(r"第\s*(\d+)\s*集\s*[：:]", outline)]
    continuous = numbers == list(range(1, len(numbers) + 1))
    return json.dumps(
        {"actual_count": len(numbers), "episodes": numbers, "continuous": continuous},
        ensure_ascii=False,
    )


def find_missing_characters(characters: str, outline: str) -> str:
    """检查人物设定里的主要人物，哪些没有在分集大纲中出现。"""
    from app.outline_validator import extract_character_names

    names = extract_character_names(characters)
    missing = [name for name in names if name not in outline]
    return json.dumps(
        {"known_names": names, "missing_names": missing},
        ensure_ascii=False,
    )


# 工具名 -> 实际要执行的 Python 函数
TOOL_IMPL = {
    "count_episodes": count_episodes,
    "find_missing_characters": find_missing_characters,
}

# 给模型看的工具说明书（OpenAI tools 格式）
TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "count_episodes",
            "description": "统计分集大纲一共有多少集，并判断集数是否从第1集连续编号。",
            "parameters": {
                "type": "object",
                "properties": {
                    "outline": {"type": "string", "description": "完整的全部集数的分集大纲文本"}
                },
                "required": ["outline"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_missing_characters",
            "description": "检查主要人物名单中，哪些人物没有在分集大纲中出现。",
            "parameters": {
                "type": "object",
                "properties": {
                    "characters": {"type": "string", "description": "人物设定全文，需包含「主要人物名单」章节"},
                    "outline": {"type": "string", "description": "完整的分集大纲文本"},
                },
                "required": ["characters", "outline"],
            },
        },
    },
]

SYSTEM_PROMPT = """你是一个短剧大纲质检助手。
你可以调用工具来检查大纲，但不要凭感觉下结论——先调用工具拿到事实，再给判断。
工具需要的参数请原样传入用户提供的文本，不要自己改写。
任务完成后，直接给出结论，不要再调用工具。"""


# ---------------------------------------------------------------------------
# 二、Agent Loop —— 这是 W1 要你自己写的部分
# ---------------------------------------------------------------------------

def run_agent(task: str, max_steps: int = MAX_STEPS) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for step in range(1, max_steps + 1):
        logger.info("===== Step %d / %d =====", step, max_steps)

        # ------------------------------------------------------------------
        # TODO 1：调用模型
        #   把 TOOLS_SPEC 作为 tools 参数传进去。
        #   注意：这一次调用之后，模型可能给你两种东西——
        #     a) 一段最终回答（message.content）
        #     b) 若干 tool_calls（模型想让你执行工具）
        # ------------------------------------------------------------------
        response = None  # ← 替换成真实的 API 调用
        raise NotImplementedError("TODO 1：调用模型")

        # ------------------------------------------------------------------
        # TODO 2：没有 tool_calls，说明模型认为任务完成
        #   取出 message.content 返回，并结束循环。
        #   想一想：如果 content 是空的，但也没有 tool_calls，该怎么办？
        # ------------------------------------------------------------------

        # ------------------------------------------------------------------
        # TODO 3：有 tool_calls，逐个执行
        #   对每一个 call：
        #     - call.function.name  -> 从 TOOL_IMPL 里找到对应函数
        #     - call.function.arguments -> 这是 JSON 字符串，先 json.loads
        #     - 调用函数，拿到字符串结果
        #   然后把每个结果以 {"role": "tool", "tool_call_id": ..., "content": ...}
        #   的形式追加回 messages，再进入下一轮循环。
        #
        #   三个必须处理的失败路径：
        #     1. 工具名不存在
        #     2. arguments 不是合法 JSON
        #     3. 工具函数本身抛异常
        #   处理方式：把错误信息当作工具结果返回给模型，让它自己决定下一步。
        #   不要 raise，也不要 try/except 后静默忽略。
        # ------------------------------------------------------------------

    # 走到这里说明循环没自己停下来
    raise RuntimeError(
        f"超过 {max_steps} 步仍未完成任务。可能原因：模型在反复调用工具，"
        "或工具的返回结果没有让模型获得新信息。"
    )


# ---------------------------------------------------------------------------
# 三、测试数据与入口
# ---------------------------------------------------------------------------

SAMPLE_CHARACTERS = """## 人物设定
1. 林晓：28 岁，律师，性格冷静，目标是查出父亲死因。
2. 陈默：35 岁，刑警，表面敷衍，真实动机是保护林晓。
3. 周远：42 岁，企业高管，反派，动机是掩盖当年事故。
4. 苏晴：26 岁，记者，林晓的闺蜜，后期会立场反转。

## 主要人物名单
林晓、陈默、周远、苏晴
"""

SAMPLE_OUTLINE = """第1集：归来
- 本集目标：林晓回到家乡
- 核心冲突：与陈默重逢时气氛紧张
- 关键剧情：林晓发现父亲遗物中有疑点
- 本集反转或进展：遗物里出现陌生名字
- 结尾钩子：有人跟踪她

第2集：旧案
- 本集目标：林晓调取旧卷宗
- 核心冲突：卷宗缺失关键页
- 关键剧情：陈默暗中帮她
- 本集反转或进展：缺失页出现在她家门口
- 结尾钩子：卷宗上的指纹属于周远

第4集：对峙
- 本集目标：林晓正面质问周远
- 核心冲突：周远否认并反击
- 关键剧情：一位老邻居提供了新线索
- 本集反转或进展：陈默的真实身份曝光
- 结尾钩子：林晓的车被人动了手脚
"""


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    task = (
        "请检查下面这份分集大纲：\n"
        "1. 集数是否完整、是否从第 1 集连续编号？\n"
        "2. 主要人物名单里的人，是否都在大纲里出场了？\n\n"
        f"【人物设定】\n{SAMPLE_CHARACTERS}\n\n"
        f"【分集大纲】\n{SAMPLE_OUTLINE}\n"
    )

    try:
        answer = run_agent(task)
    except NotImplementedError as exc:
        print(f"\n还没开始写：{exc}")
        print("先去实现上面的 TODO 1 / 2 / 3，再运行这个文件。\n")
        sys.exit(1)

    print("\n===== Agent 最终回答 =====")
    print(answer)


if __name__ == "__main__":
    main()
