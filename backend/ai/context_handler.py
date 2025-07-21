import re
import json
import logging
from typing import Any, Dict, Optional
from backend.ai.models import ProjectContext, UserInput

logger = logging.getLogger(__name__)

class ProjectContextHandler:
    """
    Handles processing of user input for document generation, including:
    - Extracting JSON overrides from natural language prompts
    - Validating and sanitizing input
    - Building ProjectContext objects
    """

    JSON_PATTERN = re.compile(r'\{[\s\S]*?\}', re.MULTILINE)

    @staticmethod
    def extract_json_overrides(prompt_text: str) -> Dict[str, Any]:
        """
        Extract a JSON object from the end of a freeform prompt text, if present.
        Returns an empty dict if no valid JSON is found.
        """
        if not prompt_text or not prompt_text.strip():
            return {}
        matches = ProjectContextHandler.JSON_PATTERN.findall(prompt_text)
        for match in reversed(matches):  # Prefer last JSON block
            try:
                overrides = json.loads(match)
                if isinstance(overrides, dict):
                    logger.info("Extracted JSON overrides from prompt.")
                    return overrides
            except Exception as e:
                logger.debug(f"Failed to parse JSON from prompt: {e}")
        return {}

    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        Basic sanitization for user input (strip, collapse whitespace).
        """
        if not text:
            return ''
        return re.sub(r'\s+', ' ', text.strip())

    @classmethod
    def build_project_context(cls, user_input: UserInput) -> ProjectContext:
        """
        Build a ProjectContext from UserInput, extracting JSON overrides from prompt if needed.
        """
        prompt_text = cls.sanitize_input(user_input.prompt_text)
        # Prefer explicit json_overrides, else extract from prompt
        json_overrides = user_input.json_overrides or cls.extract_json_overrides(prompt_text)
        strict_vars = user_input.strict_vars or {}
        return ProjectContext(
            project_name=cls.sanitize_input(user_input.project_name),
            project_description=cls.sanitize_input(user_input.project_description),
            prompt_text=prompt_text,
            json_overrides=json_overrides,
            strict_vars=strict_vars
        )

    @staticmethod
    def validate_project_context(context: ProjectContext) -> Optional[str]:
        """
        Validate a ProjectContext. Returns None if valid, else error message.
        """
        if not context.project_name:
            return "Project name is required."
        if not context.project_description:
            return "Project description is required."
        if not context.prompt_text:
            return "Prompt text is required."
        # Optionally, check for forbidden keys in overrides, etc.
        return None