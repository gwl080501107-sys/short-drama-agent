
import re


def validate_episode_count(outline: str, expected_count: int) -> dict:
    """
    检查分集大纲的集数是否正确。
    """
    # 提取类似“第1集：”“第 2 集：”的集数标题
    matches = re.findall(
        r"第\s*(\d+)\s*集\s*[：:]",
        outline
    )

    # 将字符串集数转换为整数
    actual_episodes = [int(num) for num in matches]

    # 检查实际集数是否与预期一致
    count_correct = len(actual_episodes) == expected_count

    # 检查集数是否从 1 开始连续排列
    sequence_correct = (
        actual_episodes == list(range(1, expected_count + 1))
    )

    return {
        "expected_count": expected_count,
        "actual_count": len(actual_episodes),
        "actual_episodes": actual_episodes,
        "count_correct": count_correct,
        "sequence_correct": sequence_correct,
        "valid": count_correct and sequence_correct
    }

def validate_character_names(
    outline: str,
    known_names: list[str]
) -> dict:
    """
    检查人物设定中的主要人物是否出现在分集大纲中。
    """
    present_names = []
    missing_names = []

    for name in known_names:
        if name in outline:
            present_names.append(name)
        else:
            missing_names.append(name)

    return {
        "known_names": known_names,
        "present_names": present_names,
        "missing_names": missing_names,
        "valid": len(missing_names) == 0
    }

def extract_character_names(characters: str) -> list[str]:
    """
    从人物设定中提取主要人物名单。
    """
    match = re.search(
        r"主要人物名单\s*\n([\s\S]*?)(?=\n\s*#|\Z)",
        characters
    )

    if not match:
        return []

    names_text = match.group(1).strip()

    names = re.split(r"[、，,；;\n]+", names_text)

    return [
        name.strip()
        for name in names
        if name.strip()
    ]