from typing import Dict, Any, List

from .base_parser import BaseParser


class ComplexityAnalysisParser(BaseParser):
    """Parser for complexity analysis responses from LLM"""

    @classmethod
    def parse(cls, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured complexity analysis.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Dictionary containing parsed complexity analysis
        """
        try:
            # First try to parse as JSON
            data = cls._try_json_parse(response)
            if data:
                return cls._validate_and_clean(data)

            # If JSON parsing fails, try to extract structured data
            return cls._extract_structured_data(response)

        except Exception as e:
            raise ValueError(f"Failed to parse complexity analysis: {str(e)}")

    @classmethod
    def _validate_and_clean(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the parsed data"""
        required_fields = ["analysis", "story_points", "complexity_level"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Clean and validate story points
        try:
            data["story_points"] = int(data["story_points"])
        except (ValueError, TypeError):
            data["story_points"] = 0

        # Ensure complexity level is valid
        valid_levels = ["Low", "Medium", "High"]
        if data["complexity_level"] not in valid_levels:
            data["complexity_level"] = "Medium"

        # Ensure lists are present
        data["technical_factors"] = data.get("technical_factors", [])
        data["risk_factors"] = data.get("risk_factors", [])

        return data

    @classmethod
    def _extract_structured_data(cls, text: str) -> Dict[str, Any]:
        """Extract structured data from text when JSON parsing fails"""
        lines = text.split("\n")
        data: Dict[str, Any] = {
            "analysis": "",
            "story_points": 0,
            "complexity_level": "Medium",
            "effort_estimate": "",
            "technical_factors": [],
            "risk_factors": []
        }

        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to identify sections
            lower_line = line.lower()
            if "analysis:" in lower_line:
                current_section = "analysis"
                data["analysis"] = line.split(":", 1)[1].strip()
            elif "story points:" in lower_line:
                try:
                    points = int(line.split(":", 1)[1].strip())
                    data["story_points"] = points
                except (ValueError, IndexError):
                    pass
            elif "complexity:" in lower_line or "complexity level:" in lower_line:
                level = line.split(":", 1)[1].strip()
                if any(valid in level for valid in ["Low", "Medium", "High"]):
                    data["complexity_level"] = next(
                        valid for valid in ["Low", "Medium", "High"]
                        if valid in level
                    )
            elif "effort estimate:" in lower_line:
                data["effort_estimate"] = line.split(":", 1)[1].strip()
            elif "technical factors:" in lower_line:
                current_section = "technical_factors"
            elif "risk factors:" in lower_line:
                current_section = "risk_factors"
            elif current_section in ["technical_factors", "risk_factors"]:
                # Add bullet points to respective lists
                if line.startswith(("-", "*", "•")):
                    item = line.lstrip("-*• ").strip()
                    if item:
                        data[current_section].append(item)

        return data 