
import logging
import os

from dotenv import load_dotenv
from openai import OpenAI


logger = logging.getLogger(__name__)

# 加载项目根目录中的 .env 文件
load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise RuntimeError(
        "未读取到 DEEPSEEK_API_KEY，请检查项目根目录下的 .env 文件"
    )

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
    timeout=600.0,
    max_retries=2,
)


def generate_story_summary(
    genre: str,
    idea: str,
    episode_count: int,
    episode_duration: int,
    style: str,
) -> str:
    """根据用户输入生成短剧故事梗概。"""

    system_prompt = """
你是一名专业的中国竖屏短剧编剧。

创作要求：
1. 开头快速进入冲突，避免冗长铺垫。
2. 剧情要有明确的目标、阻碍和反转。
3. 人物动机合理，前后剧情保持一致。
4. 故事适合竖屏短剧，节奏紧凑。
5. 结尾留下值得继续观看的悬念。

请输出：
一、短剧名称
二、一句话卖点
三、故事背景
四、完整故事梗概
五、核心爽点与主要反转
六、结局设计

当前只生成整部短剧的故事梗概，不要展开每一集的完整对白。
"""

    user_prompt = f"""
请根据以下要求创作一部短剧：

题材：{genre}
故事创意：{idea}
总集数：{episode_count} 集
每集时长：约 {episode_duration} 分钟
风格：{style}

请确保故事规模适合上述集数和时长。
"""

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=False,
        max_tokens=4000,
    )

    content = response.choices[0].message.content

    if not content or not content.strip():
        raise RuntimeError("DeepSeek 返回的故事梗概为空")

    return content.strip()


def generate_characters(summary: str) -> str:
    """根据故事梗概生成主要人物设定。"""

    system_prompt = """
你是一名专业的中国竖屏短剧编剧。

请根据用户提供的故事梗概，设计 3 到 6 个主要人物。

每个人物必须包含：
1. 姓名
2. 年龄
3. 身份
4. 性格特点
5. 核心目标
6. 真实动机
7. 人物弱点
8. 与主角的关系
9. 后续剧情中的成长或反转方向

创作要求：
- 人物设定必须符合原故事梗概。
- 人物之间要有明确的利益冲突。
- 反派必须有合理的行为动机。
- 不要擅自改变故事的核心设定。
- 不要生成分集剧情或完整对白。

请使用中文，以清晰的结构输出。
要求：
1. 人物设定结束后，必须增加“## 主要人物名单”章节。
2. 该章节只列出本次实际设定的主要人物姓名。
3. 姓名之间使用中文顿号“、”分隔。
4. 人物名单中的姓名必须与上文人物设定完全一致。
"""

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"请根据以下故事梗概生成人物设定：\n\n{summary}"
            }
        ],
        stream=False,
        max_tokens=30000,
    )

    content = response.choices[0].message.content
    finish_reason = response.choices[0].finish_reason

    print(f"人物生成结束原因：{finish_reason}")
    print(f"本次生成 Token 数：{response.usage.completion_tokens}")

    if not content or not content.strip():
        raise RuntimeError("DeepSeek 返回的人物设定为空")

    if finish_reason == "length":
        raise RuntimeError(
            "人物设定生成被 Token 长度限制截断，请调整生成策略"
        )

    return content.strip()


def generate_episode_outline(
    summary: str,
    characters: str,
    episode_count: int,
) -> str:
    """根据故事梗概和人物设定，分批生成分集大纲。"""

    batch_size = 5
    all_outlines = []
    previous_outline = ""

    # 每次生成 5 集，例如 1-5、6-10、11-15、16-20
    for start_episode in range(1, episode_count + 1, batch_size):
        end_episode = min(
            start_episode + batch_size - 1,
            episode_count
        )

        system_prompt = """
你是一名专业的中国竖屏短剧编剧。

请根据故事梗概、人物设定和已有剧情，生成指定集数范围的分集大纲。

创作要求：
1. 只能生成用户指定范围内的集数，不得少集或多集。
2. 剧情必须围绕故事梗概展开，不得改变核心主线。
3. 人物姓名、身份、性格和动机必须与人物设定一致。
4. 不得擅自创造重要角色；如确有必要引入新角色，必须合理且明确其身份。
5. 每集都要推动主线或人物关系发展。
6. 剧情节奏紧凑，每集都要有明确的冲突或进展。
7. 适当安排有铺垫的反转，避免反转重复。
8. 每集结尾都要设置悬念、危机或新的剧情期待。
9. 不要生成完整对白，只输出分集大纲。
10. 后续集数必须承接已有剧情，不得重复已经发生的关键事件。
11. 最后一集必须收束核心冲突。

每集严格按照以下格式输出：

第N集：标题
- 本集目标：
- 核心冲突：
- 关键剧情：
- 本集反转或进展：
- 结尾钩子：

只输出指定范围内的分集大纲，不要输出开场白或额外总结。
"""

        user_prompt = f"""
请生成第 {start_episode} 集到第 {end_episode} 集的分集大纲。

【故事梗概】
{summary}

【人物设定】
{characters}
"""

        if previous_outline:
            user_prompt += f"""

【上一批已生成的剧情，请承接，不要重复】
{previous_outline}
"""

        user_prompt += f"""

【本次生成范围】
第 {start_episode} 集至第 {end_episode} 集。

请确保集数连续、人物设定一致、剧情前后连贯。
"""

        print(
            f"正在生成第 {start_episode}-{end_episode} 集大纲..."
        )

        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            stream=False,
            max_tokens=40000,
        )

        content = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        print(f"本批生成结束原因：{finish_reason}")
        print(
            f"本批生成 Token 数："
            f"{response.usage.completion_tokens}"
        )

        if not content or not content.strip():
            raise RuntimeError(
                f"第 {start_episode}-{end_episode} 集生成结果为空"
            )

        if finish_reason == "length":
            raise RuntimeError(
                f"第 {start_episode}-{end_episode} 集被 Token 长度限制截断，"
                "请缩短每集内容或进一步减小每批集数"
            )

        batch_outline = content.strip()
        all_outlines.append(batch_outline)
        previous_outline = batch_outline

    # 合并所有批次，返回完整分集大纲
    return "\n\n".join(all_outlines)

def review_episode_outline(
    summary: str,
    characters: str,
    outline: str
) -> str:
    """
    使用 AI 审核分集大纲的剧情质量。
    """

    system_prompt = """
你是一名专业的中国竖屏短剧编剧和剧本审核人员。

请审核输入的短剧分集大纲，重点检查：

1. 剧情逻辑：是否存在前后矛盾、因果关系不成立或关键情节缺少解释。
2. 人物一致性：人物身份、人物关系、行为动机是否前后矛盾。
3. 反转质量：反转是否有合理铺垫，是否过于突然。
4. 结尾钩子：每集结尾是否有悬念、危机或足够的追看动力。

审核规则：
- 只根据输入内容判断，不要自行补充不存在的剧情事实。
- 不要把尚未解释的情节直接认定为逻辑错误。
- 每个问题尽可能指出具体集数和对应情节。
- 如果信息不足，请明确说明“信息不足，无法判断”。
- 不要直接重写剧本。

请严格按照以下结构输出：

## 一、整体评价
简要评价故事结构和整体质量。

## 二、发现的问题
逐条列出问题，每条包含：
- 涉及集数
- 问题类型
- 对应剧情
- 问题原因
- 修改建议

如果没有发现明确问题，请说明。

## 三、各集结尾钩子评价
指出钩子较弱或缺少明显悬念的集数，并解释原因。

## 四、优先修改建议
列出最值得优先修改的三个问题。
"""

    user_prompt = f"""
请审核以下短剧内容。

【故事梗概】
{summary}

【主要人物设定】
{characters}

【分集大纲】
{outline}
"""

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_tokens=60000,
        temperature=0.3
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("AI 未返回剧情审核结果")

    if response.choices[0].finish_reason == "length":
        raise RuntimeError("剧情审核结果被截断，请缩短输入内容后重试")

    return content

def revise_episode_outline(
    summary: str,
    characters: str,
    outline: str,
    review: str
) -> str:
    """
    根据 AI 审核意见修改分集大纲。
    """

    system_prompt = """
你是一名专业的中国竖屏短剧编剧。

请根据提供的故事梗概、人物设定、原始分集大纲和审核意见，
修改原始分集大纲。

修改要求：
1. 保留原故事核心设定、主要人物关系和主线冲突。
2. 优先解决审核意见中指出的剧情逻辑和人物一致性问题。
3. 不要只写修改说明，必须输出修改后的完整分集大纲。
4. 保留原始总集数，集数必须从第1集连续编号。
5. 每集都要包含标题、核心冲突、关键剧情、反转或进展、结尾钩子。
6. 不要为了修复问题而随意新增重要人物。
7. 如果需要增加时间跨度，必须明确交代时间变化。
8. 技术和法律情节必须有合理铺垫，不要用无法解释的操作强行解决冲突。
9. 保持竖屏短剧节奏，强化冲突、反转和集尾悬念。
10. 只输出修改后的完整分集大纲，不要输出分析过程。
"""

    user_prompt = f"""
【故事梗概】
{summary}

【人物设定】
{characters}

【原始分集大纲】
{outline}

【审核意见】
{review}

请根据审核意见修改完整分集大纲。
"""

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_tokens=393216,
        temperature=0.4
    )

    content = response.choices[0].message.content
    choice = response.choices[0]
    logger.info("大纲修改 finish_reason: %s", choice.finish_reason)
    logger.info("大纲修改 content: %r", choice.message.content)
    logger.info("大纲修改 usage: %s", response.usage)
    if not content:
        raise RuntimeError("AI 未返回修改后的分集大纲")

    if response.choices[0].finish_reason == "length":
        raise RuntimeError("修改后的大纲被截断，请分批修改")

    return content