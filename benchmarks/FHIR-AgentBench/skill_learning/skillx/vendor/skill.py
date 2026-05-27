# Vendored verbatim from SkillX/core/skill.py (arXiv 2604.04804).
# Preserves the exact JSON serialization schema for skillx_library.json compatibility.
"""Skill data models for SkillX."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Metadata for a skill."""
    skill_type: Literal["functional", "atomic"] = "functional"
    source_tasks: List[str] = field(default_factory=list)
    source_tool: Optional[str] = None
    cluster_id: Optional[int] = None
    extraction_epoch: int = 1
    created_at: Optional[str] = None
    modified_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_type": self.skill_type,
            "source_tasks": self.source_tasks,
            "source_tool": self.source_tool,
            "cluster_id": self.cluster_id,
            "extraction_epoch": self.extraction_epoch,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillMetadata":
        return cls(
            skill_type=data.get("skill_type", "functional"),
            source_tasks=data.get("source_tasks", []),
            source_tool=data.get("source_tool"),
            cluster_id=data.get("cluster_id"),
            extraction_epoch=data.get("extraction_epoch", 1),
            created_at=data.get("created_at"),
            modified_at=data.get("modified_at"),
        )


@dataclass
class Skill:
    """Base skill class with unified 5-key schema."""
    name: str
    document: str
    content: str
    tools: List[str]
    metadata: SkillMetadata = field(default_factory=SkillMetadata)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "document": self.document,
            "content": self.content,
            "tools": self.tools,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        metadata = data.get("metadata", {})
        if isinstance(metadata, dict):
            metadata = SkillMetadata.from_dict(metadata)
        return cls(
            name=data["name"],
            document=data["document"],
            content=data["content"],
            tools=data.get("tools", []),
            metadata=metadata,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "Skill":
        return cls.from_dict(json.loads(json_str))

    def get_embedding_text(self) -> str:
        return f"{self.name}\n{self.document}\n{self.content}"

    @property
    def skill_type(self) -> str:
        return self.metadata.skill_type


class FunctionalSkill(Skill):
    """Functional skill for step-based extraction."""

    def __post_init__(self):
        if self.metadata.skill_type != "functional":
            self.metadata.skill_type = "functional"


class AtomicSkill(Skill):
    """Atomic skill for tool-centric extraction."""

    def __post_init__(self):
        if self.metadata.skill_type != "atomic":
            self.metadata.skill_type = "atomic"
        if self.metadata.source_tool is None:
            self.metadata.source_tool = self.name


@dataclass
class PlanSkill:
    """Planning skill for task-level planning."""
    task: str
    plan: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "plan": self.plan,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanSkill":
        return cls(
            task=data["task"],
            plan=data["plan"],
            metadata=data.get("metadata", {}),
        )

    def get_steps(self) -> List[str]:
        steps = []
        for line in self.plan.split("\n"):
            line = line.strip()
            if line.startswith("# step"):
                steps.append(line)
        return steps


@dataclass
class SkillLibrary:
    """Container for all skill types."""
    version: str = "1.0"
    benchmark: str = "appworld"
    created_at: Optional[str] = None
    planning: Dict[str, PlanSkill] = field(default_factory=dict)
    functional: List[Skill] = field(default_factory=list)
    atomic: List[Skill] = field(default_factory=list)
    embeddings_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if not self.embeddings_config:
            self.embeddings_config = {
                "model": "Qwen3-Embedding-8B",
                "index_type": "FAISS-HNSW",
            }

    def add_plan(self, task: str, plan: PlanSkill) -> None:
        self.planning[task] = plan

    def add_functional_skill(self, skill: Skill) -> None:
        if skill.metadata.skill_type != "functional":
            skill.metadata.skill_type = "functional"
        self.functional.append(skill)

    def add_atomic_skill(self, skill: Skill) -> None:
        if skill.metadata.skill_type != "atomic":
            skill.metadata.skill_type = "atomic"
        self.atomic.append(skill)

    def get_all_skills(self) -> List[Skill]:
        return self.functional + self.atomic

    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        for skill in self.functional + self.atomic:
            if skill.name == name:
                return skill
        return None

    def get_skills_by_tool(self, tool_name: str) -> List[Skill]:
        return [
            skill for skill in self.functional + self.atomic
            if tool_name in skill.tools
        ]

    def get_missing_tools(self, used_tools: set) -> set:
        existing_tool_names = set()
        for skill in self.atomic:
            existing_tool_names.add(skill.name)
        return used_tools - existing_tool_names

    def get_all_tool_names(self) -> set:
        tool_names = set()
        for skill in self.atomic:
            tool_names.add(skill.name)
            tool_names.update(skill.tools)
        for skill in self.functional:
            tool_names.update(skill.tools)
        return tool_names

    def merge(self, skills: List["Skill"], epoch: int = 1) -> None:
        """Merge new skills into the library (dedup by name)."""
        functional_tool_names: set = set()
        for s in self.functional:
            functional_tool_names.update(s.tools)
        for s in skills:
            if s.metadata.skill_type == "functional":
                functional_tool_names.update(s.tools)

        dropped_atomic: list = []

        for skill in skills:
            skill.metadata.extraction_epoch = epoch
            skill.metadata.modified_at = datetime.now().isoformat()

            if skill.metadata.skill_type == "functional":
                existing = self.get_skill_by_name(skill.name)
                if existing is None:
                    self.functional.append(skill)
                else:
                    idx = self.functional.index(existing)
                    self.functional[idx] = skill
            else:
                if skill.name in functional_tool_names:
                    dropped_atomic.append(skill.name)
                    continue
                existing = self.get_skill_by_name(skill.name)
                if existing is None:
                    self.atomic.append(skill)
                else:
                    idx = self.atomic.index(existing)
                    self.atomic[idx] = skill

        if dropped_atomic:
            logger.info(
                "Dropped %d atomic skill(s) already covered by functional skills: %s",
                len(dropped_atomic), dropped_atomic
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "benchmark": self.benchmark,
            "created_at": self.created_at,
            "skills": {
                "planning": {
                    task: plan.to_dict() for task, plan in self.planning.items()
                },
                "functional": [skill.to_dict() for skill in self.functional],
                "atomic": [skill.to_dict() for skill in self.atomic],
            },
            "embeddings": self.embeddings_config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillLibrary":
        skills_data = data.get("skills", {})
        planning = {}
        for task, plan_data in skills_data.get("planning", {}).items():
            planning[task] = PlanSkill.from_dict(plan_data)
        functional = [Skill.from_dict(s) for s in skills_data.get("functional", [])]
        atomic = [Skill.from_dict(s) for s in skills_data.get("atomic", [])]
        return cls(
            version=data.get("version", "1.0"),
            benchmark=data.get("benchmark", "appworld"),
            created_at=data.get("created_at"),
            planning=planning,
            functional=functional,
            atomic=atomic,
            embeddings_config=data.get("embeddings", {}),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "SkillLibrary":
        return cls.from_dict(json.loads(json_str))

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "SkillLibrary":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())
