"""
SkillRepository — reads base skills (read-only) and manages learned skills
(read-write).

Skill files are Markdown with YAML frontmatter:

    ---
    name: skill_name
    description: one-line description
    tags: [tag1, tag2]
    version: 1
    ---

    Skill body text...
"""

import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import yaml


def _parse_skill_file(path: Path) -> Dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if match:
        meta = yaml.safe_load(match.group(1)) or {}
        body = match.group(2).strip()
    else:
        meta = {}
        body = text.strip()
    return {
        "name": meta.get("name", path.stem),
        "description": meta.get("description", ""),
        "tags": meta.get("tags") or [],
        "version": meta.get("version", 0),
        "provenance": meta.get("provenance"),  # None for pre-provenance skills
        "content": body,
    }


def _write_skill_file(path: Path, name: str, description: str, content: str,
                      tags: List[str], version: int,
                      provenance: Optional[Dict] = None) -> None:
    meta = {
        "name": name,
        "description": description,
        "tags": tags,
        "version": version,
    }
    if provenance:
        meta["provenance"] = provenance
    text = (
        f"---\n{yaml.dump(meta, default_flow_style=False).strip()}\n---\n\n"
        f"{content}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f".{path.stem}.",
        suffix=".tmp",
    ) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


class SkillRepository:
    """
    Manages two directories of skills:
    - base_dir: read-only, always loaded (e.g. skills/base/)
    - learned_dir: read-write, grown during a run (e.g. run_dir/skills/learned/)
    """

    def __init__(self, base_dir: Path, learned_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.learned_dir = Path(learned_dir)
        self.learned_dir.mkdir(parents=True, exist_ok=True)

    def load_all(self) -> List[Dict]:
        """Return all skills: base first, then learned."""
        skills = []
        for directory in (self.base_dir, self.learned_dir):
            for path in sorted(directory.glob("*.md")):
                skills.append(_parse_skill_file(path))
        return skills

    def exists_in_learned(self, name: str) -> bool:
        return (self.learned_dir / f"{name}.md").exists()

    def add(self, name: str, description: str, content: str,
            tags: Optional[List[str]] = None,
            provenance: Optional[Dict] = None) -> None:
        path = self.learned_dir / f"{name}.md"
        _write_skill_file(path, name, description, content, tags or [], version=1,
                          provenance=provenance)

    def modify(self, name: str, description: str, content: str,
               tags: Optional[List[str]] = None,
               provenance: Optional[Dict] = None) -> None:
        path = self.learned_dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Cannot modify non-existent learned skill: {name}")
        existing = _parse_skill_file(path)

        # Archive the current version before overwriting so history is queryable
        history_dir = self.learned_dir / ".history"
        history_dir.mkdir(exist_ok=True)
        shutil.copy2(path, history_dir / f"{name}_v{existing.get('version', 0)}.md")

        # Attach parent_version so the history chain is traceable
        prov = dict(provenance or {})
        prov["parent_version"] = existing.get("version", 0)
        _write_skill_file(
            path,
            name,
            description,
            content,
            tags if tags is not None else existing["tags"],
            version=existing["version"] + 1,
            provenance=prov,
        )

    def get_history(self, name: str) -> List[Dict]:
        """Return archived previous versions of a skill, oldest first."""
        history_dir = self.learned_dir / ".history"
        if not history_dir.exists():
            return []
        versions = []
        for path in sorted(history_dir.glob(f"{name}_v*.md")):
            try:
                versions.append(_parse_skill_file(path))
            except Exception:
                pass
        return versions

    def delete(self, name: str) -> None:
        path = self.learned_dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Cannot delete non-existent learned skill: {name}")
        path.unlink()

    def learned_count(self) -> int:
        return len(list(self.learned_dir.glob("*.md")))

    def snapshot(self) -> List[Dict]:
        """Return a serializable snapshot of the current learned skills."""
        return [_parse_skill_file(p) for p in sorted(self.learned_dir.glob("*.md"))]

    def fork(self) -> "SkillRepository":
        """
        Create a temporary copy of this repository's learned/ dir.
        The returned repo shares the same base_dir but writes to a temp dir.
        Call .cleanup() on the returned repo when done.
        """
        tmp_dir = Path(tempfile.mkdtemp(prefix="skill_fork_"))
        if self.learned_dir.exists():
            shutil.copytree(self.learned_dir, tmp_dir / "learned")
        else:
            (tmp_dir / "learned").mkdir(parents=True)
        forked = SkillRepository(self.base_dir, tmp_dir / "learned")
        forked._tmp_root = tmp_dir
        return forked

    def cleanup(self) -> None:
        """Remove the temp directory created by fork(), if any."""
        tmp_root = getattr(self, "_tmp_root", None)
        if tmp_root and Path(tmp_root).exists():
            shutil.rmtree(tmp_root, ignore_errors=True)
