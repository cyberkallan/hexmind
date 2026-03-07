"""
HexMind Skills Library — wrapper for SkillsManager
Provides the SkillsLibrary class expected by core/app.py
"""

from brain.skills import SkillsManager


class SkillsLibrary:
    """High-level skills interface used by app.py."""

    def __init__(self):
        self._mgr = SkillsManager()

    def show_menu(self, console):
        """Show interactive skills menu."""
        self._mgr.show_menu(console)

    def list_installed(self) -> list:
        """Return list of installed skill IDs."""
        return self._mgr.get_installed()

    def install(self, skill_id, console=None) -> bool:
        return self._mgr.install(skill_id, console)

    def uninstall(self, skill_id, console=None) -> bool:
        return self._mgr.uninstall(skill_id, console)

    def get_skill_content(self, skill_id: str) -> str:
        return self._mgr.get_skill_content(skill_id)

    def search_skills(self, query: str) -> list:
        return self._mgr.search_skills(query)
