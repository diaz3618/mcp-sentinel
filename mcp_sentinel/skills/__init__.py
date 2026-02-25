"""Skills system — reusable skill packages.

Provides:
- ``SkillManifest`` — parsed manifest.json
- ``SkillManager`` — lifecycle management
- ``InstalledSkill`` / ``SkillStatus`` — installed skill metadata
"""

from mcp_sentinel.skills.manager import InstalledSkill, SkillManager, SkillStatus
from mcp_sentinel.skills.manifest import SkillManifest

__all__ = [
    "InstalledSkill",
    "SkillManager",
    "SkillManifest",
    "SkillStatus",
]
