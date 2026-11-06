
from pydantic import BaseModel, Field


class DramaRequest(BaseModel):
    # 短剧题材，例如：都市逆袭、豪门、悬疑
    genre: str = Field(description="短剧题材")

    # 用户提供的故事创意
    idea: str = Field(min_length=10, description="故事创意")

    # 全剧集数，默认20集
    episode_count: int = Field(default=20, ge=1, le=1000)

    # 每集时长，单位：分钟
    episode_duration: int = Field(default=2, ge=1, le=20)

    # 剧本风格，例如：强反转、爽文、悬疑
    style: str = Field(default="强冲突、强反转")

class CharacterRequest(BaseModel):
    summary: str = Field(
        min_length=20,
        description="已经生成的短剧故事梗概"
    )


class EpisodeOutlineRequest(BaseModel):
    summary: str = Field(
        min_length=20,
        description="短剧故事梗概"
    )
    characters: str = Field(
        min_length=20,
        description="主要人物设定"
    )
    episode_count: int = Field(
        default=20,
        ge=1,
        le=100,
        description="短剧总集数"
    )

class OutlineReviewRequest(BaseModel):
    summary: str = Field(
        min_length=20,
        description="短剧故事梗概"
    )
    characters: str = Field(
        min_length=20,
        description="主要人物设定"
    )
    outline: str = Field(
        min_length=20,
        description="完整分集大纲"
    )
class OutlineReviseRequest(BaseModel):
    summary: str = Field(
        min_length=20,
        description="故事梗概"
    )
    characters: str = Field(
        min_length=20,
        description="人物设定"
    )
    outline: str = Field(
        min_length=20,
        description="原始分集大纲"
    )
    review: str = Field(
        min_length=20,
        description="AI 剧情审核意见"
    )