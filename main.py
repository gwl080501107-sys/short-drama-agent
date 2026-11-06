
import logging

from fastapi import FastAPI, HTTPException
from app.outline_validator import validate_episode_count, validate_character_names, extract_character_names
from app.llm_client import (
    generate_story_summary,
    generate_characters,
    generate_episode_outline, review_episode_outline, revise_episode_outline,
)
from app.schemas import (
    DramaRequest,
    CharacterRequest,
    EpisodeOutlineRequest, OutlineReviewRequest, OutlineReviseRequest,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ShortDrama Agent")


@app.get("/")
def home():
    return {
        "message": "ShortDrama Agent 已启动",
        "version": "0.1.0"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/dramas/validate")
def validate_drama(request: DramaRequest):
    return {
        "message": "短剧生成参数校验成功",
        "data": request.model_dump()
    }


@app.post("/dramas/generate-summary")
def generate_summary(request: DramaRequest):
    try:
        summary = generate_story_summary(
            genre=request.genre,
            idea=request.idea,
            episode_count=request.episode_count,
            episode_duration=request.episode_duration,
            style=request.style,
        )

        return {
            "message": "故事梗概生成成功",
            "data": {
                "genre": request.genre,
                "episode_count": request.episode_count,
                "summary": summary,
            },
        }

    except Exception:
        logger.exception("生成故事梗概失败")
        raise HTTPException(
            status_code=502,
            detail="大模型调用失败，请检查 API 配置、网络或服务状态",
        )


@app.post("/dramas/generate-characters")
def generate_drama_characters(request: CharacterRequest):
    try:
        characters = generate_characters(
            summary=request.summary
        )

        return {
            "message": "人物设定生成成功",
            "data": {
                "characters": characters
            }
        }

    except Exception:
        logger.exception("生成人物设定失败")
        raise HTTPException(
            status_code=502,
            detail="人物设定生成失败，请检查大模型调用或服务状态"
        )


@app.post("/dramas/generate-outline")
def generate_drama_outline(request: EpisodeOutlineRequest):
    try:
        # 1. 调用 DeepSeek 生成分集大纲
        outline = generate_episode_outline(
            summary=request.summary,
            characters=request.characters,
            episode_count=request.episode_count
        )

        # 2. 自动检查集数和顺序
        validation = validate_episode_count(
            outline=outline,
            expected_count=request.episode_count
        )
        known_names = extract_character_names(request.characters)

        if not known_names:
            character_validation = {
                "valid": False,
                "message": "未能提取主要人物名单，请检查人物设定格式",
                "known_names": [],
                "present_names": [],
                "missing_names": []
            }
        else:
            character_validation = validate_character_names(
                outline=outline,
                known_names=known_names
            )

        # 3. 返回大纲和校验结果
        return {
            "message": "分集大纲生成成功",
            "data": {
                "episode_count": request.episode_count,
                "outline": outline,
                "validation": validation,
                "character_validation": character_validation
            }
        }

    except Exception:
        logger.exception("生成分集大纲失败")
        raise HTTPException(
            status_code=502,
            detail="生成分集大纲失败，请稍后重试"
        )

@app.post("/dramas/review-outline")
def review_drama_outline(request: OutlineReviewRequest):
    try:
        review = review_episode_outline(
            summary=request.summary,
            characters=request.characters,
            outline=request.outline
        )

        return {
            "message": "剧情审核完成",
            "data": {
                "review": review
            }
        }

    except Exception:
        logger.exception("剧情审核失败")
        raise HTTPException(
            status_code=502,
            detail="剧情审核失败，请稍后重试"
        )

import re

@app.post("/dramas/revise-outline")
def revise_drama_outline(request: OutlineReviseRequest):
    try:
        revised_outline = revise_episode_outline(
            summary=request.summary,
            characters=request.characters,
            outline=request.outline,
            review=request.review
        )

        # 统计原始大纲的集数
        expected_count = len(
            re.findall(r"第\s*\d+\s*集\s*[：:]", request.outline)
        )

        # 校验修改后的集数
        validation = validate_episode_count(
            outline=revised_outline,
            expected_count=expected_count
        )

        return {
            "message": "分集大纲修改完成",
            "data": {
                "original_outline": request.outline,
                "revised_outline": revised_outline,
                "validation": validation
            }
        }

    except Exception as e:
        logger.exception("修改分集大纲失败：%s", str(e))

        raise HTTPException(
            status_code=502,
            detail=f"修改分集大纲失败：{str(e)}"
        )