#!/usr/bin/env python3
"""
Skill Router — maps incoming ACP jobs to the right skill.

Loads all skills from the skills/ directory and routes jobs based on
keyword matching in the job description.
"""

import importlib
import os
import sys
from pathlib import Path

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.skill_interface import BaseSkill


class SkillRouter:
    """Routes jobs to the appropriate skill based on keywords."""

    def __init__(self, skills_dir: str = None):
        self.skills_dir = Path(skills_dir or (Path(__file__).parent / "skills"))
        self.skills: dict[str, BaseSkill] = {}
        self.load_skills()

    def load_skills(self) -> None:
        """Dynamically load all skills from the skills/ directory."""
        if not self.skills_dir.exists():
            return

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
                continue

            init_file = skill_dir / "__init__.py"
            skill_file = skill_dir / "skill.py"

            if skill_file.exists():
                try:
                    module_name = f"skills.{skill_dir.name}.skill"
                    spec = importlib.util.spec_from_file_location(
                        module_name, str(skill_file)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find the skill class (subclass of BaseSkill, not BaseSkill itself)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type)
                            and issubclass(attr, BaseSkill)
                            and attr is not BaseSkill):
                            skill = attr()
                            self.skills[skill.name] = skill
                            break
                except Exception as e:
                    print(f"⚠️  Failed to load skill {skill_dir.name}: {e}")

    def route(self, job: dict) -> BaseSkill | None:
        """Find the best matching skill for a job."""
        desc = (job.get("description", "") or job.get("name", "")).lower()

        # Exact keyword match
        for skill in self.skills.values():
            if skill.can_handle(job):
                return skill

        # Fallback: fuzzy keyword match
        best_score = 0
        best_skill = None
        for skill in self.skills.values():
            score = sum(1 for kw in skill.keywords if kw.lower() in desc)
            if score > best_score:
                best_score = score
                best_skill = skill

        return best_skill if best_score > 0 else None

    def list_skills(self) -> list[dict]:
        """List all loaded skills."""
        return [
            {
                "name": s.name,
                "displayName": s.display_name,
                "categories": s.categories,
                "keywords": s.keywords,
            }
            for s in self.skills.values()
        ]
