from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class A2ATTaskPromptRendererTest(unittest.TestCase):
    def test_shared_task_prompt_renderer_builds_plain_prompt_body(self) -> None:
        from a2a_t.prompt.task_rendering import TaskPromptRenderer

        renderer = TaskPromptRenderer()
        prompt_text = renderer.render(
            template_text="Site: {site}\nNotes: {additional_notes}",
            slots={"site": "Site A", "additional_notes": None},
            scenario_code="ran-energy-saving",
            language="en-US",
            description="Used for energy saving analysis.",
        )

        self.assertEqual(prompt_text, "Site: Site A\nNotes: ")
        self.assertNotIn("scenario_code:", prompt_text)
        self.assertNotIn("language:", prompt_text)
        self.assertNotIn("---", prompt_text)

    def test_render_supports_double_braced_placeholders(self) -> None:
        from a2a_t.prompt.task_rendering import TaskPromptRenderer

        renderer = TaskPromptRenderer()
        prompt_text = renderer.render(
            template_text="Topic: {{topic}}\nCondition: {{condition}}",
            slots={"topic": "Incident", "condition": "critical alert"},
            scenario_code="subscribe-incident",
            language="zh-CN",
            description="Used for incident subscription prompts.",
        )

        self.assertEqual(prompt_text, "Topic: Incident\nCondition: critical alert")

    def test_render_keeps_only_slot_value_for_section_with_slot_header_body(self) -> None:
        from a2a_t.prompt.task_rendering import TaskPromptRenderer

        renderer = TaskPromptRenderer()
        prompt_text = renderer.render(
            template_text=(
                "## Task Type\n"
                "Diagnosis\n\n"
                "## Task Target\n"
                "{{task_target}}（Required）\n\n"
                "Requirement: explain the target.\n"
                "Example: complete the diagnosis.\n\n"
                "## Expected Output\n"
                "{{expected_output}}（Optional）\n"
            ),
            slots={
                "task_target": "Complete the diagnosis and provide remediation advice.",
                "expected_output": "Return a structured diagnosis result.",
            },
            scenario_code="private-line-complaint",
            language="en-US",
            description="Used for private line complaint prompts.",
        )

        self.assertEqual(
            prompt_text,
            "## Task Type\n"
            "Diagnosis\n\n"
            "## Task Target\n"
            "Complete the diagnosis and provide remediation advice.\n\n"
            "## Expected Output\n"
            "Return a structured diagnosis result.\n",
        )

    def test_render_preserves_regular_inline_placeholder_content(self) -> None:
        from a2a_t.prompt.task_rendering import TaskPromptRenderer

        renderer = TaskPromptRenderer()
        prompt_text = renderer.render(
            template_text=(
                "## Subscription\n"
                "Please subscribe to {{topic}} incidents.\n\n"
                "## Condition\n"
                "{{condition}}（Optional）\n"
                "Requirement: describe the filter.\n"
            ),
            slots={"topic": "network", "condition": "critical only"},
            scenario_code="subscribe-incident",
            language="en-US",
            description="Used for incident subscription prompts.",
        )

        self.assertEqual(
            prompt_text,
            "## Subscription\n"
            "Please subscribe to network incidents.\n\n"
            "## Condition\n"
            "critical only\n",
        )

    def test_render_raises_when_template_references_unknown_slot(self) -> None:
        from a2a_t.prompt.task_rendering import TaskPromptRenderer
        from a2a_t.prompt.task_rendering.errors import TaskPromptRenderError

        renderer = TaskPromptRenderer()

        with self.assertRaises(TaskPromptRenderError):
            renderer.render(
                template_text="Site: {site}\nTime Range: {time_range}",
                slots={"site": "Site A"},
                scenario_code="ran-energy-saving",
                language="en-US",
                description="Used for energy saving analysis.",
            )

    def test_render_raises_when_template_is_invalid(self) -> None:
        from a2a_t.prompt.task_rendering import TaskPromptRenderer
        from a2a_t.prompt.task_rendering.errors import TaskPromptRenderError

        renderer = TaskPromptRenderer()

        with self.assertRaises(TaskPromptRenderError):
            renderer.render(
                template_text="Site: {site",
                slots={"site": "Site A"},
                scenario_code="ran-energy-saving",
                language="en-US",
                description="Used for energy saving analysis.",
            )


if __name__ == "__main__":
    unittest.main()
