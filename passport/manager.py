"""
Passport Manager interface for loading, binding, validating, and serializing Agent Passports.

Supports dynamic runtime loading from external configuration files and dictionary payloads.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from passport.schema import AgentPassport
from config.settings import get_settings


class PassportManager:
    """Manages runtime loading, binding, serialization, and validation of Agent Passports."""

    def __init__(self):
        self._current_passport: Optional[AgentPassport] = None

    def load_from_file(self, file_path: Optional[str] = None) -> AgentPassport:
        """
        Dynamically load and validate an Agent Passport from an external JSON configuration file.
        If file_path is omitted, loads from the configured passport_file_path setting.
        """
        if file_path is None:
            file_path = get_settings().passport_file_path or "config/passport.json"

        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Passport configuration file not found at path: '{file_path}'")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        self._current_passport = AgentPassport.from_dict(raw_data)
        return self._current_passport

    def load_from_dict(self, data: Dict[str, Any]) -> AgentPassport:
        """Parse, validate, and bind raw passport dictionary data to active session."""
        self._current_passport = AgentPassport.from_dict(data)
        return self._current_passport

    def load_passport(self, passport_input: Union[Dict[str, Any], str]) -> AgentPassport:
        """Backward-compatible loader accepting either a dictionary or file path."""
        if isinstance(passport_input, str):
            return self.load_from_file(passport_input)
        return self.load_from_dict(passport_input)

    def get_active_passport(self) -> Optional[AgentPassport]:
        """Return currently loaded AgentPassport instance."""
        return self._current_passport

    def serialize(self) -> Dict[str, Any]:
        """Serialize active passport to dictionary representation."""
        if self._current_passport is None:
            raise ValueError("No active passport loaded to serialize.")
        return self._current_passport.to_dict()

    def deserialize(self, payload: Union[str, Dict[str, Any]]) -> AgentPassport:
        """Deserialize payload (JSON string or dict) into a validated AgentPassport."""
        if isinstance(payload, str):
            passport = AgentPassport.from_json(payload)
        else:
            passport = AgentPassport.from_dict(payload)
        self._current_passport = passport
        return passport
