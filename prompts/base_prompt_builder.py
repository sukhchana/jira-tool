from typing import Dict, Any, List


class BasePromptBuilder:
    """Base class for all prompt builders with common utilities"""

    @staticmethod
    def format_dict_for_prompt(d: Dict[str, Any]) -> str:
        """Format a dictionary for use in prompts"""
        result = []
        for key, value in d.items():
            formatted_key = key.replace("_", " ").title()
            if isinstance(value, list):
                result.append(f"{formatted_key}:")
                result.extend([f"- {item}" for item in value])
            else:
                result.append(f"{formatted_key}: {value}")
        return "\n".join(result)

    @staticmethod
    def wrap_in_tags(content: str, tag: str) -> str:
        """Wrap content in XML-style tags"""
        return f"<{tag}>\n{content}\n</{tag}>"

    @staticmethod
    def format_list_items(items: list) -> str:
        """Format a list of items into a bullet-point string"""
        return "\n".join(f"- {item}" for item in items)

    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """Format code block with optional language specification"""
        return f"```{language}\n{code}\n```"

    @staticmethod
    def format_scenarios(scenarios: list) -> str:
        """Format Gherkin scenarios"""
        formatted_scenarios = []
        for scenario in scenarios:
            formatted_scenarios.append(
                f"Scenario: {scenario['name']}\n"
                f"Given {scenario['given']}\n"
                f"When {scenario['when']}\n"
                f"Then {scenario['then']}"
            )
            if "and" in scenario:
                formatted_scenarios[-1] += f"\nAnd {scenario['and']}"
        return "\n\n".join(formatted_scenarios)

    @staticmethod
    def format_user_stories(user_stories: List[Dict[str, Any]]) -> str:
        """Format user stories for use in prompts"""
        formatted = []
        for story in user_stories:
            formatted.append(f"Story: {story.get('title', story.get('name', 'Unnamed'))}")
            formatted.append(f"Description: {story.get('description', '')}")
            formatted.append(f"Technical Domain: {story.get('technical_domain', '')}")
            formatted.append("")
        return "\n".join(formatted)

    @staticmethod
    def format_epic_analysis(epic_analysis: Dict[str, Any]) -> str:
        """Format epic analysis for use in prompts"""
        formatted = []
        if "technical_domains" in epic_analysis:
            formatted.append("Technical Domains:")
            formatted.extend([f"- {domain}" for domain in epic_analysis["technical_domains"]])
            formatted.append("")
        if "core_requirements" in epic_analysis:
            formatted.append("Core Requirements:")
            formatted.extend([f"- {req}" for req in epic_analysis["core_requirements"]])
        return "\n".join(formatted)
