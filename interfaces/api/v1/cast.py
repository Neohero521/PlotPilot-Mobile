"""Cast API routes"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from application.services.cast_service import CastService
from application.dtos.cast_dto import CastGraphDTO, CastSearchResultDTO, CastCoverageDTO
from interfaces.api.dependencies import get_cast_service
from domain.shared.exceptions import EntityNotFoundError


router = APIRouter(tags=["cast"])


# Request Models
class StoryEventRequest(BaseModel):
    """Story event request"""
    id: str = Field(..., description="Event ID")
    summary: str = Field(..., description="Event summary")
    chapter_id: Optional[int] = Field(None, description="Chapter ID")
    importance: str = Field("normal", description="Importance level (normal/key)")


class CharacterRequest(BaseModel):
    """Character request"""
    id: str = Field(..., description="Character ID")
    name: str = Field(..., description="Character name")
    aliases: List[str] = Field(default_factory=list, description="Character aliases")
    role: str = Field("", description="Character role")
    traits: str = Field("", description="Character traits")
    note: str = Field("", description="Character note")
    story_events: List[StoryEventRequest] = Field(default_factory=list, description="Story events")


class RelationshipRequest(BaseModel):
    """Relationship request"""
    id: str = Field(..., description="Relationship ID")
    source_id: str = Field(..., description="Source character ID")
    target_id: str = Field(..., description="Target character ID")
    label: str = Field("", description="Relationship label")
    note: str = Field("", description="Relationship note")
    directed: bool = Field(True, description="Is directed relationship")
    story_events: List[StoryEventRequest] = Field(default_factory=list, description="Story events")


class UpdateCastGraphRequest(BaseModel):
    """Update cast graph request"""
    version: int = Field(2, description="Cast graph version")
    characters: List[CharacterRequest] = Field(..., description="Characters")
    relationships: List[RelationshipRequest] = Field(..., description="Relationships")


# Routes
@router.get("/novels/{novel_id}/cast", response_model=CastGraphDTO)
async def get_cast_graph(
    novel_id: str,
    service: CastService = Depends(get_cast_service)
):
    """获取人物关系图（从三元组自动生成）

    关系图现在从 novel_knowledge.json 的 facts 字段自动提取：
    - 人物节点：predicate="是" 且 object 包含"主角"、"配角"等关键词
    - 人物关系：predicate 为"师徒"、"父子"、"朋友"等关系谓词

    Args:
        novel_id: Novel ID
        service: Cast service

    Returns:
        Cast graph DTO（自动生成）

    Raises:
        HTTPException: If knowledge not found
    """
    cast_graph = service.get_cast_graph(novel_id)
    if cast_graph is None:
        # 尚无 knowledge 文件时返回空图
        return CastGraphDTO(version=2, characters=[], relationships=[])
    return cast_graph


# PUT 接口已移除：关系图现在从 novel_knowledge.json 的三元组自动生成
# 要编辑人物关系，请直接修改 /api/v1/novels/{novel_id}/knowledge 中的 facts 字段
#
# 人物节点规范：
# {
#   "subject": "张三",
#   "predicate": "是",
#   "object": "主角" | "配角" | "人物",
#   "note": "人物描述"
# }
#
# 人物关系规范：
# {
#   "subject": "张三",
#   "predicate": "师徒" | "父子" | "朋友" | "敌对" | ...,
#   "object": "李四",
#   "note": "关系说明"
# }


@router.get("/novels/{novel_id}/cast/search", response_model=CastSearchResultDTO)
async def search_cast(
    novel_id: str,
    q: str,
    service: CastService = Depends(get_cast_service)
):
    """Search characters and relationships in cast graph

    Args:
        novel_id: Novel ID
        q: Search query
        service: Cast service

    Returns:
        Search results DTO

    Raises:
        HTTPException: If cast graph not found
    """
    try:
        return service.search_cast(novel_id, q)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/novels/{novel_id}/cast/coverage", response_model=CastCoverageDTO)
async def get_cast_coverage(
    novel_id: str,
    service: CastService = Depends(get_cast_service)
):
    """Get cast coverage analysis for a novel

    Analyzes character mentions in chapters and compares with cast graph.

    Args:
        novel_id: Novel ID
        service: Cast service

    Returns:
        Cast coverage DTO

    Raises:
        HTTPException: If cast graph not found
    """
    try:
        return service.get_cast_coverage(novel_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
