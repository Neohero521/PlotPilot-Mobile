"""Cast application service - 从三元组自动生成关系图"""
import logging
import re
import json
from typing import Optional, List, Dict, Set
from pathlib import Path
from domain.cast.aggregates.cast_graph import CastGraph
from domain.cast.entities.character import Character
from domain.cast.entities.relationship import Relationship
from domain.cast.entities.story_event import StoryEvent
from domain.cast.value_objects.character_id import CharacterId
from domain.cast.value_objects.relationship_id import RelationshipId
from domain.novel.value_objects.novel_id import NovelId
from domain.shared.exceptions import EntityNotFoundError
from application.dtos.cast_dto import (
    CastGraphDTO,
    CastSearchResultDTO,
    CastCoverageDTO,
    CharacterCoverageDTO,
    BibleCharacterDTO,
    QuotedTextDTO
)

logger = logging.getLogger(__name__)


# 人物角色关键词（用于识别人物节点）
CHARACTER_ROLE_KEYWORDS = {
    "主角", "配角", "反派", "人物", "角色",
    "主要角色", "次要角色", "重要角色",
    "男主", "女主", "男配", "女配"
}

# 人物关系谓词（用于识别关系边）
RELATIONSHIP_PREDICATES = {
    "师徒", "父子", "母子", "父女", "母女", "兄弟", "姐妹", "夫妻",
    "朋友", "好友", "挚友", "知己",
    "敌对", "仇敌", "对手", "竞争",
    "上下级", "主仆", "雇佣",
    "认识", "相识", "熟悉"
}


class CastService:
    """Cast application service

    从 novel_knowledge.json 的三元组中自动提取人物关系图。
    """

    def __init__(self, storage_root: Path):
        """Initialize service

        Args:
            storage_root: Root path for storage (e.g., ./data)
        """
        self.storage_root = storage_root

    def _load_knowledge(self, novel_id: str) -> Optional[dict]:
        """加载知识图谱数据

        Args:
            novel_id: Novel ID

        Returns:
            Knowledge data dict or None
        """
        knowledge_path = self.storage_root / "novels" / novel_id / "novel_knowledge.json"
        if not knowledge_path.exists():
            logger.debug(f"Knowledge file not found: {knowledge_path}")
            return None

        try:
            return json.loads(knowledge_path.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning(f"Failed to load knowledge from {knowledge_path}: {e}")
            return None

    def _extract_characters_from_facts(self, facts: List[dict]) -> List[Character]:
        """从三元组中提取人物节点

        识别规则：
        1. predicate="是" 且 object 包含人物角色关键词
        2. subject 或 object 出现在关系谓词的三元组中

        Args:
            facts: 三元组列表

        Returns:
            人物列表
        """
        # 第一步：识别明确标记为人物的实体
        character_map: Dict[str, Dict] = {}

        for fact in facts:
            subject = fact.get("subject", "").strip()
            predicate = fact.get("predicate", "").strip()
            obj = fact.get("object", "").strip()
            note = fact.get("note", "")

            # 规则1：predicate="是" 且 object 是人物角色
            if predicate == "是" and any(keyword in obj for keyword in CHARACTER_ROLE_KEYWORDS):
                if subject not in character_map:
                    character_map[subject] = {
                        "name": subject,
                        "role": obj,
                        "traits": "",
                        "note": note,
                        "aliases": []
                    }
                else:
                    # 更新角色信息
                    character_map[subject]["role"] = obj
                    if note:
                        character_map[subject]["note"] = note

            # 规则2：predicate 是能力、目标等属性
            elif predicate in ["能力是", "目标是", "特点是", "性格是"]:
                if subject not in character_map:
                    character_map[subject] = {
                        "name": subject,
                        "role": "",
                        "traits": obj,
                        "note": note,
                        "aliases": []
                    }
                else:
                    # 追加特质
                    if character_map[subject]["traits"]:
                        character_map[subject]["traits"] += f"; {obj}"
                    else:
                        character_map[subject]["traits"] = obj

        # 第二步：从关系谓词中识别隐含的人物
        for fact in facts:
            subject = fact.get("subject", "").strip()
            predicate = fact.get("predicate", "").strip()
            obj = fact.get("object", "").strip()

            if predicate in RELATIONSHIP_PREDICATES:
                # subject 和 object 都应该是人物
                if subject and subject not in character_map:
                    character_map[subject] = {
                        "name": subject,
                        "role": "",
                        "traits": "",
                        "note": "",
                        "aliases": []
                    }
                if obj and obj not in character_map:
                    character_map[obj] = {
                        "name": obj,
                        "role": "",
                        "traits": "",
                        "note": "",
                        "aliases": []
                    }

        # 转换为 Character 对象
        characters = []
        for idx, (name, data) in enumerate(character_map.items()):
            char_id = f"char_{idx + 1}"
            character = Character(
                id=CharacterId(char_id),
                name=data["name"],
                aliases=data["aliases"],
                role=data["role"],
                traits=data["traits"],
                note=data["note"],
                story_events=[]
            )
            characters.append(character)

        logger.info(f"→ 从三元组中提取了 {len(characters)} 个人物")
        return characters

    def _extract_relationships_from_facts(
        self,
        facts: List[dict],
        characters: List[Character]
    ) -> List[Relationship]:
        """从三元组中提取人物关系

        Args:
            facts: 三元组列表
            characters: 人物列表

        Returns:
            关系列表
        """
        # 构建人物名称到ID的映射
        name_to_char: Dict[str, Character] = {char.name: char for char in characters}

        relationships = []
        rel_idx = 0

        for fact in facts:
            subject = fact.get("subject", "").strip()
            predicate = fact.get("predicate", "").strip()
            obj = fact.get("object", "").strip()
            note = fact.get("note", "")

            # 只处理关系谓词
            if predicate not in RELATIONSHIP_PREDICATES:
                continue

            # 检查 subject 和 object 是否都是已识别的人物
            if subject not in name_to_char or obj not in name_to_char:
                continue

            source_char = name_to_char[subject]
            target_char = name_to_char[obj]

            rel_idx += 1
            relationship = Relationship(
                id=RelationshipId(f"rel_{rel_idx}"),
                source_id=source_char.id,
                target_id=target_char.id,
                label=predicate,
                note=note,
                directed=True,  # 默认有向
                story_events=[]
            )
            relationships.append(relationship)

        logger.info(f"→ 从三元组中提取了 {len(relationships)} 条关系")
        return relationships

    def get_cast_graph(self, novel_id: str) -> Optional[CastGraphDTO]:
        """从三元组自动生成关系图

        Args:
            novel_id: Novel ID

        Returns:
            CastGraphDTO if knowledge exists, None otherwise
        """
        logger.info(f"→ 从三元组生成关系图: novel_id={novel_id}")

        # 加载知识图谱
        knowledge = self._load_knowledge(novel_id)
        if knowledge is None:
            logger.debug(f"Knowledge not found for novel {novel_id}")
            return None

        facts = knowledge.get("facts", [])
        if not facts:
            logger.debug(f"No facts found for novel {novel_id}")
            return CastGraphDTO(version=2, characters=[], relationships=[])

        # 提取人物和关系
        characters = self._extract_characters_from_facts(facts)
        relationships = self._extract_relationships_from_facts(facts, characters)

        # 构建 CastGraph 领域对象
        cast_graph = CastGraph(
            id=f"cast_{novel_id}",
            novel_id=NovelId(novel_id),
            version=2,
            characters=characters,
            relationships=relationships
        )

        logger.info(f"✓ 关系图生成完成: {len(characters)} 人物, {len(relationships)} 关系")
        return CastGraphDTO.from_domain(cast_graph)

    def search_cast(self, novel_id: str, query: str) -> CastSearchResultDTO:
        """搜索人物和关系

        Args:
            novel_id: Novel ID
            query: Search query

        Returns:
            CastSearchResultDTO with matching characters and relationships

        Raises:
            EntityNotFoundError: If cast graph not found
        """
        cast_dto = self.get_cast_graph(novel_id)
        if cast_dto is None:
            raise EntityNotFoundError("CastGraph", f"for novel {novel_id}")

        # 重建领域对象以使用搜索方法
        characters = []
        for char_dto in cast_dto.characters:
            character = Character(
                id=CharacterId(char_dto.id),
                name=char_dto.name,
                aliases=char_dto.aliases,
                role=char_dto.role,
                traits=char_dto.traits,
                note=char_dto.note,
                story_events=[]
            )
            characters.append(character)

        relationships = []
        for rel_dto in cast_dto.relationships:
            relationship = Relationship(
                id=RelationshipId(rel_dto.id),
                source_id=CharacterId(rel_dto.source_id),
                target_id=CharacterId(rel_dto.target_id),
                label=rel_dto.label,
                note=rel_dto.note,
                directed=rel_dto.directed,
                story_events=[]
            )
            relationships.append(relationship)

        cast_graph = CastGraph(
            id=f"cast_{novel_id}",
            novel_id=NovelId(novel_id),
            version=2,
            characters=characters,
            relationships=relationships
        )

        matched_chars = cast_graph.search_characters(query)
        matched_rels = cast_graph.search_relationships(query)

        return CastSearchResultDTO.from_domain_lists(matched_chars, matched_rels)

    def get_cast_coverage(self, novel_id: str) -> CastCoverageDTO:
        """分析人物覆盖率

        Args:
            novel_id: Novel ID

        Returns:
            CastCoverageDTO with coverage analysis

        Raises:
            EntityNotFoundError: If cast graph not found
        """
        cast_dto = self.get_cast_graph(novel_id)
        if cast_dto is None:
            raise EntityNotFoundError("CastGraph", f"for novel {novel_id}")

        # 查找章节文件
        novel_path = self.storage_root / "novels" / novel_id
        chapter_files = list(novel_path.glob("chapter_*.md"))
        chapter_files_scanned = len(chapter_files)

        # 构建人物名称索引
        char_name_map: Dict[str, str] = {}  # name -> char_id
        for char in cast_dto.characters:
            char_name_map[char.name] = char.id
            for alias in char.aliases:
                char_name_map[alias] = char.id

        # 扫描章节中的人物提及
        char_mentions: Dict[str, Set[int]] = {char.id: set() for char in cast_dto.characters}

        for chapter_file in chapter_files:
            match = re.search(r'chapter_(\d+)\.md', chapter_file.name)
            if not match:
                continue
            chapter_id = int(match.group(1))

            try:
                content = chapter_file.read_text(encoding='utf-8')
                for name, char_id in char_name_map.items():
                    if name in content:
                        char_mentions[char_id].add(chapter_id)
            except Exception as e:
                logger.warning(f"Failed to read chapter file {chapter_file}: {e}")

        # 构建覆盖率列表
        characters_coverage = []
        for char in cast_dto.characters:
            chapter_ids = sorted(char_mentions.get(char.id, set()))
            characters_coverage.append(CharacterCoverageDTO(
                id=char.id,
                name=char.name,
                mentioned=len(chapter_ids) > 0,
                chapter_ids=chapter_ids
            ))

        # 分析 Bible 覆盖率
        bible_not_in_cast = self._analyze_bible_coverage(novel_id, cast_dto, chapter_files)

        # 分析引号文本
        quoted_not_in_cast = self._analyze_quoted_text(cast_dto, chapter_files)

        return CastCoverageDTO(
            chapter_files_scanned=chapter_files_scanned,
            characters=characters_coverage,
            bible_not_in_cast=bible_not_in_cast,
            quoted_not_in_cast=quoted_not_in_cast
        )

    def _analyze_bible_coverage(
        self,
        novel_id: str,
        cast_dto: CastGraphDTO,
        chapter_files: List[Path]
    ) -> List[BibleCharacterDTO]:
        """分析 Bible 中的人物是否在关系图中

        Args:
            novel_id: Novel ID
            cast_dto: Cast graph DTO
            chapter_files: Chapter files

        Returns:
            Bible characters not in cast
        """
        bible_path = self.storage_root / "novels" / novel_id / "bible.json"
        if not bible_path.exists():
            return []

        try:
            bible_data = json.loads(bible_path.read_text(encoding='utf-8'))
            bible_characters = bible_data.get("characters", [])
        except Exception as e:
            logger.warning(f"Failed to load bible data: {e}")
            return []

        # 获取关系图中的人物名称
        cast_names = set()
        for char in cast_dto.characters:
            cast_names.add(char.name)
            cast_names.update(char.aliases)

        # 查找不在关系图中的 Bible 人物
        result = []
        for bible_char in bible_characters:
            name = bible_char.get("name", "")
            if not name or name in cast_names:
                continue

            # 检查是否在章节中提及
            chapter_ids = set()
            for chapter_file in chapter_files:
                match = re.search(r'chapter_(\d+)\.md', chapter_file.name)
                if not match:
                    continue
                chapter_id = int(match.group(1))

                try:
                    content = chapter_file.read_text(encoding='utf-8')
                    if name in content:
                        chapter_ids.add(chapter_id)
                except Exception:
                    pass

            result.append(BibleCharacterDTO(
                name=name,
                role=bible_char.get("role", ""),
                in_novel_text=len(chapter_ids) > 0,
                chapter_ids=sorted(chapter_ids)
            ))

        return result

    def _analyze_quoted_text(
        self,
        cast_dto: CastGraphDTO,
        chapter_files: List[Path]
    ) -> List[QuotedTextDTO]:
        """分析引号文本中不在关系图中的人物

        Args:
            cast_dto: Cast graph DTO
            chapter_files: Chapter files

        Returns:
            Quoted text not in cast
        """
        # 获取关系图中的人物名称
        cast_names = set()
        for char in cast_dto.characters:
            cast_names.add(char.name)
            cast_names.update(char.aliases)

        # 查找引号文本
        quoted_pattern = re.compile(r'「([^」]+)」')
        quoted_mentions: Dict[str, Set[int]] = {}

        for chapter_file in chapter_files:
            match = re.search(r'chapter_(\d+)\.md', chapter_file.name)
            if not match:
                continue
            chapter_id = int(match.group(1))

            try:
                content = chapter_file.read_text(encoding='utf-8')
                for match in quoted_pattern.finditer(content):
                    text = match.group(1)
                    if text not in cast_names:
                        if text not in quoted_mentions:
                            quoted_mentions[text] = set()
                        quoted_mentions[text].add(chapter_id)
            except Exception:
                pass

        # 构建结果
        result = []
        for text, chapter_ids in quoted_mentions.items():
            result.append(QuotedTextDTO(
                text=text,
                count=len(chapter_ids),
                chapter_ids=sorted(chapter_ids)
            ))

        # 按出现次数降序排序
        result.sort(key=lambda x: x.count, reverse=True)

        return result
