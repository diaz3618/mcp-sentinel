"""Skills system — reusable skill packages.

Provides:
- ``SkillManifest`` — parsed manifest.json
- ``SkillManager`` — lifecycle management
- ``InstalledSkill`` / ``SkillStatus`` — installed skill metadata
"""

from argus_mcp.skills.manager import InstalledSkill, SkillManager, SkillStatus
from argus_mcp.skills.manifest import SkillManifest

__all__ = [
    "InstalledSkill",
    "SkillManager",
    "SkillManifest",
    "SkillStatus",
]
