
import json
import sys
import time
from pathlib import Path

import httpx


# ==================== 基础配置 ====================

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 600

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = PROJECT_ROOT / "test-results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

# 短剧基础创意：后续接口自动使用前面生成的结果
DRAMA_REQUEST = {
    "genre": "都市商战、创业逆袭",
    "idea": "一名程序员发现合伙人盗用自己的核心代码，并利用公司控制权将他逼入绝境。他与妻子联手调查证据，发现妻子曾被合伙人利用，最终通过一场知识产权与商业利益的较量完成反击。",
    "episode_count": 20,
    "episode_duration": 2,
    "style": "强冲突、强反转、爽点密集、集尾悬念",
}


# ==================== 通用工具 ====================

def save_json(filename, data):
    """保存接口结果，方便查看和断点续跑。"""
    file_path = RESULT_DIR / filename

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print(f"结果已保存：{file_path}")
    return data


def load_json(filename):
    """读取之前保存的接口结果。"""
    file_path = RESULT_DIR / filename

    if not file_path.exists():
        return None

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        print(f"复用已有结果：{file_path}")
        return data

    except (json.JSONDecodeError, OSError) as exc:
        print(f"读取结果失败，将重新请求：{filename}，原因：{exc}")
        return None


def call_api(client, step_name, method, endpoint, payload):
    """调用接口，输出耗时和详细错误。"""
    print("\n" + "=" * 70)
    print(f"执行步骤：{step_name}")
    print(f"接口地址：{method} {endpoint}")
    print("请求参数：")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    start_time = time.time()

    try:
        response = client.request(
            method=method,
            url=f"{BASE_URL}{endpoint}",
            json=payload,
        )

        elapsed = time.time() - start_time

        print(f"HTTP 状态码：{response.status_code}")
        print(f"耗时：{elapsed:.1f} 秒")

        try:
            result = response.json()
        except ValueError:
            result = {"raw_response": response.text}

        if not response.is_success:
            print("接口返回的详细错误：")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            raise RuntimeError(
                f"{step_name} 执行失败，HTTP {response.status_code}"
            )

        print(f"执行成功：{step_name}")
        return result

    except httpx.RequestError as exc:
        print(f"请求异常：{exc}")
        raise RuntimeError(
            f"无法连接后端，请检查服务是否启动：{BASE_URL}"
        ) from exc


def get_data(result, step_name):
    """统一获取 FastAPI 返回的 data 字段。"""
    data = result.get("data")

    if not isinstance(data, dict):
        raise ValueError(
            f"{step_name} 返回结果中没有有效的 data 对象："
            f"{json.dumps(result, ensure_ascii=False)}"
        )

    return data


def get_required_text(data, field, step_name):
    """获取必需的文本字段，避免把错误数据传给下一个接口。"""
    value = data.get(field)

    if not isinstance(value, str) or len(value.strip()) < 20:
        raise ValueError(
            f"{step_name} 返回的 {field} 字段不存在或内容过短。"
            f"实际返回：{json.dumps(data, ensure_ascii=False)}"
        )

    return value


def run_step(client, filename, step_name, method, endpoint, payload):
    """优先复用已保存结果，否则调用接口。"""
    cached = load_json(filename)

    if cached is not None:
        return cached

    result = call_api(
        client=client,
        step_name=step_name,
        method=method,
        endpoint=endpoint,
        payload=payload,
    )

    save_json(filename, result)
    return result


# ==================== 自动化主流程 ====================

def main():
    print("=" * 70)
    print("ShortDrama Agent 自动化测试")
    print(f"后端地址：{BASE_URL}")
    print(f"结果目录：{RESULT_DIR}")
    print("=" * 70)

    try:
        with httpx.Client(timeout=TIMEOUT) as client:

            # 1. 生成故事梗概
            summary_result = run_step(
                client=client,
                filename="01_summary.json",
                step_name="生成故事梗概",
                method="POST",
                endpoint="/dramas/generate-summary",
                payload=DRAMA_REQUEST,
            )

            summary_data = get_data(summary_result, "故事梗概接口")
            summary = get_required_text(
                summary_data, "summary", "故事梗概接口"
            )

            # 2. 生成人物设定：使用上一步的 summary
            characters_result = run_step(
                client=client,
                filename="02_characters.json",
                step_name="生成人物设定",
                method="POST",
                endpoint="/dramas/generate-characters",
                payload={"summary": summary},
            )

            characters_data = get_data(
                characters_result, "人物设定接口"
            )
            characters = get_required_text(
                characters_data, "characters", "人物设定接口"
            )

            # 3. 生成分集大纲：使用前两步的结果
            outline_result = run_step(
                client=client,
                filename="03_outline.json",
                step_name="生成分集大纲",
                method="POST",
                endpoint="/dramas/generate-outline",
                payload={
                    "summary": summary,
                    "characters": characters,
                    "episode_count": DRAMA_REQUEST["episode_count"],
                },
            )

            outline_data = get_data(outline_result, "分集大纲接口")
            outline = get_required_text(
                outline_data, "outline", "分集大纲接口"
            )

            # 4. 审核大纲
            review_result = run_step(
                client=client,
                filename="04_review.json",
                step_name="审核分集大纲",
                method="POST",
                endpoint="/dramas/review-outline",
                payload={
                    "summary": summary,
                    "characters": characters,
                    "outline": outline,
                },
            )

            review_data = get_data(review_result, "大纲审核接口")
            review = get_required_text(
                review_data, "review", "大纲审核接口"
            )

            # 5. 根据审核意见修改大纲
            revise_result = run_step(
                client=client,
                filename="05_revised_outline.json",
                step_name="根据审核意见修改大纲",
                method="POST",
                endpoint="/dramas/revise-outline",
                payload={
                    "summary": summary,
                    "characters": characters,
                    "outline": outline,
                    "review": review,
                },
            )

            revise_data = get_data(revise_result, "修改大纲接口")
            revised_outline = get_required_text(
                revise_data, "revised_outline", "修改大纲接口"
            )

            # 6. 再次审核修改后的大纲
            final_review_result = run_step(
                client=client,
                filename="06_final_review.json",
                step_name="复审修改后的大纲",
                method="POST",
                endpoint="/dramas/review-outline",
                payload={
                    "summary": summary,
                    "characters": characters,
                    "outline": revised_outline,
                },
            )

            final_review_data = get_data(
                final_review_result, "最终审核接口"
            )
            final_review = get_required_text(
                final_review_data, "review", "最终审核接口"
            )

            # 7. 输出流程摘要
            report = {
                "genre": DRAMA_REQUEST["genre"],
                "episode_count": DRAMA_REQUEST["episode_count"],
                "summary": summary,
                "characters": characters,
                "original_outline": outline,
                "first_review": review,
                "revised_outline": revised_outline,
                "final_review": final_review,
                "outline_validation": outline_data.get("validation"),
                "character_validation": outline_data.get(
                    "character_validation"
                ),
                "revised_validation": revise_data.get("validation"),
            }

            save_json("07_pipeline_report.json", report)

            print("\n" + "=" * 70)
            print("自动化流程全部完成！")
            print("=" * 70)
            print(f"结果目录：{RESULT_DIR}")
            print("生成的文件：")

            for file_path in sorted(RESULT_DIR.glob("*.json")):
                print(f"  - {file_path.name}")

            print("\n分集大纲校验结果：")
            print(json.dumps(
                report["outline_validation"],
                ensure_ascii=False,
                indent=2,
            ))

            print("\n人物校验结果：")
            print(json.dumps(
                report["character_validation"],
                ensure_ascii=False,
                indent=2,
            ))

            print("\n修改后大纲校验结果：")
            print(json.dumps(
                report["revised_validation"],
                ensure_ascii=False,
                indent=2,
            ))

    except Exception as exc:
        print("\n" + "!" * 70)
        print("自动化流程中断")
        print(f"错误原因：{exc}")
        print("已完成的步骤结果保存在 test-results 目录中。")
        print("修复问题后可以重新运行脚本。")
        print("!" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
