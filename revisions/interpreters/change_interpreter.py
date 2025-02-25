import json
import re
from typing import Dict, Any

from loguru import logger

from .base_interpreter import BaseInterpreter
from ..models import DateTimeEncoder


class ChangeInterpreter(BaseInterpreter):
    """Interpreter for generating specific changes to apply"""

    async def generate_changes(
            self,
            ticket_data: Dict[str, Any],
            interpreted_changes: str
    ) -> Dict[str, Any]:
        """Generate specific changes to apply to a ticket"""
        try:
            prompt = f"""
            Please analyze the interpreted changes and generate the specific updates needed for this ticket.
            
            Current Ticket:
            {json.dumps(ticket_data, indent=2, cls=DateTimeEncoder)}
            
            Interpreted Changes:
            {interpreted_changes}
            
            Please provide the exact changes to make to the ticket in the following format:
            
            <changes>
            {{
                "field_updates": {{
                    "field_name": "new_value",
                    ...
                }},
                "list_append": {{
                    "field_name": ["value_to_append", ...],
                    ...
                }},
                "list_remove": {{
                    "field_name": ["value_to_remove", ...],
                    ...
                }}
            }}
            </changes>
            
            Rules:
            1. field_updates: Direct value replacements
            2. list_append: Values to add to list fields
            3. list_remove: Values to remove from list fields
            4. Only include fields that need to change
            5. Use exact field names from the current ticket
            6. The response MUST be valid JSON within the <changes> tags
            7. All three keys (field_updates, list_append, list_remove) MUST be included even if empty
            """

            response = await self.generate_interpretation(prompt)

            # Extract the JSON from the response
            changes_match = re.search(r'<changes>\s*({.*?})\s*</changes>', response, re.DOTALL)
            if not changes_match:
                logger.error(f"No valid changes found in response, attempting to parse full response as JSON")
                # Try to extract any JSON-like structure in the response
                json_match = re.search(r'({.*})', response.replace('\n', ' '), re.DOTALL)
                if json_match:
                    try:
                        changes = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse response as JSON: {response}")
                        changes = {"field_updates": {}, "list_append": {}, "list_remove": {}}
                else:
                    logger.error(f"No JSON structure found in response: {response}")
                    changes = {"field_updates": {}, "list_append": {}, "list_remove": {}}
            else:
                try:
                    changes = json.loads(changes_match.group(1))
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse changes JSON: {changes_match.group(1)}")
                    changes = {"field_updates": {}, "list_append": {}, "list_remove": {}}

            # Ensure the changes structure has all required keys
            required_keys = ["field_updates", "list_append", "list_remove"]
            for key in required_keys:
                if key not in changes:
                    changes[key] = {}

            return changes

        except Exception as e:
            logger.error(f"Failed to generate changes: {str(e)}")
            logger.error(f"Ticket data: {json.dumps(ticket_data, cls=DateTimeEncoder)}")
            logger.error(f"Interpreted changes: {interpreted_changes}")
            raise
