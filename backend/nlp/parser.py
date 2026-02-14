"""NLP parser that converts natural language to PolicyConfiguration using Claude."""

import json
import os
import re
from dataclasses import asdict

import anthropic

from simulation.core.config import PolicyConfiguration
from nlp.prompts import SYSTEM_PROMPT, REFINEMENT_PROMPT


class PolicyParser:
    """Parses natural language policy descriptions into PolicyConfiguration objects."""

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Set it to your Anthropic API key."
            )
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    async def parse(self, text: str) -> tuple[PolicyConfiguration, str]:
        """Parse natural language text into a PolicyConfiguration.

        Args:
            text: Natural language policy description.

        Returns:
            Tuple of (PolicyConfiguration, human-readable summary).

        Raises:
            ValueError: If the response requires clarification or cannot be parsed.
        """
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
        )

        response_text = message.content[0].text
        parsed = self._extract_json(response_text)

        # Check if clarification is needed
        if "clarification_needed" in parsed:
            raise ValueError(parsed["clarification_needed"])

        config = self._dict_to_config(parsed)
        summary = parsed.get("description", "Policy configuration parsed successfully.")
        return config, summary

    async def refine(
        self, text: str, current_config: PolicyConfiguration
    ) -> tuple[PolicyConfiguration, str]:
        """Refine an existing PolicyConfiguration based on follow-up instructions.

        Args:
            text: Natural language refinement instruction.
            current_config: The current PolicyConfiguration to modify.

        Returns:
            Tuple of (updated PolicyConfiguration, human-readable summary).

        Raises:
            ValueError: If the response requires clarification or cannot be parsed.
        """
        current_dict = asdict(current_config)
        prompt = REFINEMENT_PROMPT.format(
            current_config=json.dumps(current_dict, indent=2),
            user_text=text,
        )

        message = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text
        parsed = self._extract_json(response_text)

        if "clarification_needed" in parsed:
            raise ValueError(parsed["clarification_needed"])

        config = self._dict_to_config(parsed)
        summary = parsed.get("description", "Policy configuration refined successfully.")
        return config, summary

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from Claude's response, handling ```json blocks or raw JSON.

        Args:
            text: Raw response text from Claude.

        Returns:
            Parsed dictionary.

        Raises:
            ValueError: If no valid JSON can be extracted.
        """
        # Try to find ```json ... ``` block first
        json_block_pattern = r"```json\s*([\s\S]*?)\s*```"
        match = re.search(json_block_pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find any ``` ... ``` block
        code_block_pattern = r"```\s*([\s\S]*?)\s*```"
        match = re.search(code_block_pattern, text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to parse the entire response as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find a JSON object in the text
        brace_pattern = r"\{[\s\S]*\}"
        match = re.search(brace_pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Could not extract valid JSON from response. Raw response:\n{text}"
        )

    def _dict_to_config(self, data: dict) -> PolicyConfiguration:
        """Convert a parsed dictionary to a PolicyConfiguration.

        Only sets fields that are present in the dictionary; others keep defaults.

        Args:
            data: Dictionary of configuration fields.

        Returns:
            PolicyConfiguration instance.
        """
        config = PolicyConfiguration()
        field_map = {
            "density_multiplier": float,
            "target_tract_ids": list,
            "enforcement_budget_multiplier": float,
            "enforcement_target_tracts": list,
            "treatment_beds_added": int,
            "budget_reduction_pct": float,
            "protected_departments": list,
            "fare_multiplier": float,
            "service_frequency_multiplier": float,
            "permit_timeline_reduction_pct": float,
            "permit_target_types": list,
            "description": str,
            "name": str,
        }

        for field_name, field_type in field_map.items():
            if field_name in data:
                value = data[field_name]
                if field_type == float and isinstance(value, (int, float)):
                    value = float(value)
                elif field_type == int and isinstance(value, (int, float)):
                    value = int(value)
                elif field_type == list and isinstance(value, list):
                    value = [str(v) for v in value]
                setattr(config, field_name, value)

        return config
