import json
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any
from io import StringIO

from loguru import logger

from .base_interpreter import BaseInterpreter
from ..models import DateTimeEncoder


class ChangeInterpreter(BaseInterpreter):
    """Interpreter for generating specific changes to apply"""

    def _fallback_regex_extraction(self, xml_content: str) -> Dict[str, Any]:
        """Fallback method to extract changes using regex when XML parsing fails"""
        logger.info("Attempting fallback regex extraction")
        result = {"field_updates": {}, "list_append": {}, "list_remove": {}}
        
        # Extract field updates using regex
        field_updates_match = re.search(r'<field_updates>(.*?)</field_updates>', xml_content, re.DOTALL)
        if field_updates_match:
            field_updates_content = field_updates_match.group(1)
            field_patterns = re.finditer(r'<field\s+name="([^"]+)">(.*?)</field>', field_updates_content, re.DOTALL)
            for match in field_patterns:
                field_name = match.group(1)
                field_value = match.group(2).strip()
                result["field_updates"][field_name] = field_value
        
        # Extract list appends using regex
        list_append_match = re.search(r'<list_append>(.*?)</list_append>', xml_content, re.DOTALL)
        if list_append_match:
            list_append_content = list_append_match.group(1)
            field_patterns = re.finditer(r'<field\s+name="([^"]+)">(.*?)</field>', list_append_content, re.DOTALL)
            for match in field_patterns:
                field_name = match.group(1)
                field_content = match.group(2)
                items = re.findall(r'<item>(.*?)</item>', field_content, re.DOTALL)
                if items:
                    result["list_append"][field_name] = [item.strip() for item in items]
        
        # Extract list removes using regex
        list_remove_match = re.search(r'<list_remove>(.*?)</list_remove>', xml_content, re.DOTALL)
        if list_remove_match:
            list_remove_content = list_remove_match.group(1)
            field_patterns = re.finditer(r'<field\s+name="([^"]+)">(.*?)</field>', list_remove_content, re.DOTALL)
            for match in field_patterns:
                field_name = match.group(1)
                field_content = match.group(2)
                items = re.findall(r'<item>(.*?)</item>', field_content, re.DOTALL)
                if items:
                    result["list_remove"][field_name] = [item.strip() for item in items]
        
        logger.info(f"Regex fallback extracted: {result}")
        return result

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
            
            Please provide the exact changes to make to the ticket in the following XML format:
            
            <changes>
                <field_updates>
                    <field name="field_name">new value</field>
                    <!-- Additional field updates -->
                </field_updates>
                <list_append>
                    <field name="field_name">
                        <item>value to append</item>
                        <!-- Additional items -->
                    </field>
                    <!-- Additional fields -->
                </list_append>
                <list_remove>
                    <field name="field_name">
                        <item>value to remove</item>
                        <!-- Additional items -->
                    </field>
                    <!-- Additional fields -->
                </list_remove>
            </changes>
            
            Rules:
            1. field_updates: Direct value replacements - use a <field> tag with name attribute and content
            2. list_append: Values to add to list fields - use <field> with name attribute and <item> tags for each value
            3. list_remove: Values to remove from list fields - use <field> with name attribute and <item> tags for each value
            4. Only include fields that need to change
            5. Use exact field names from the current ticket 
            6. The XML must be well-formed and valid
            7. All three sections (field_updates, list_append, list_remove) MUST be included even if empty
            8. XML handles complex text better, so you can include quotes, newlines, etc. without escaping
            9. For security reasons, don't include any DOCTYPE declarations or XML processing instructions
            10. Make sure to properly close all tags (<field></field> not just <field>)
            11. Special XML characters like < > & must be properly escaped as &lt; &gt; &amp;
            
            Example:
            <changes>
                <field_updates>
                    <field name="description">This is a new description with "quotes" and
            newlines and special characters like &lt; and &gt; that XML handles well</field>
                </field_updates>
                <list_append>
                    <field name="acceptance_criteria">
                        <item>New acceptance criteria 1</item>
                        <item>New acceptance criteria 2</item>
                    </field>
                </list_append>
                <list_remove>
                    <field name="dependencies">
                        <item>Dependency to remove</item>
                    </field>
                </list_remove>
            </changes>
            
            FOCUS ON VALID XML STRUCTURE. The most important thing is that your response can be parsed as valid XML.
            """

            response = await self.generate_interpretation(prompt)

            # Extract the XML from the response
            changes_match = re.search(r'<changes>.*?</changes>', response, re.DOTALL)
            if not changes_match:
                logger.error(f"No valid XML changes found in response")
                return {"field_updates": {}, "list_append": {}, "list_remove": {}}
            
            xml_string = changes_match.group(0)
            
            # Parse the XML
            try:
                # Add a root element to handle multiple changes elements
                xml_string = f"<root>{xml_string}</root>"
                
                # Parse the XML
                root = ET.fromstring(xml_string)
                changes = root.find('changes')
                
                if changes is None:
                    logger.error("No changes element found in XML")
                    return {"field_updates": {}, "list_append": {}, "list_remove": {}}
                
                # Convert XML to dictionary
                result = {"field_updates": {}, "list_append": {}, "list_remove": {}}
                
                # Process field_updates
                field_updates = changes.find('field_updates')
                if field_updates is not None:
                    for field in field_updates.findall('field'):
                        name = field.get('name')
                        if name:
                            result["field_updates"][name] = field.text or ""
                
                # Process list_append
                list_append = changes.find('list_append')
                if list_append is not None:
                    for field in list_append.findall('field'):
                        name = field.get('name')
                        if name:
                            items = [item.text or "" for item in field.findall('item')]
                            if items:
                                result["list_append"][name] = items
                
                # Process list_remove
                list_remove = changes.find('list_remove')
                if list_remove is not None:
                    for field in list_remove.findall('field'):
                        name = field.get('name')
                        if name:
                            items = [item.text or "" for item in field.findall('item')]
                            if items:
                                result["list_remove"][name] = items
                
                return result
                
            except Exception as xml_error:
                logger.error(f"Failed to parse XML: {str(xml_error)}")
                logger.error(f"XML content: {xml_string}")
                
                # Try regex fallback if XML parsing fails
                try:
                    fallback_result = self._fallback_regex_extraction(xml_string)
                    logger.info("Successfully extracted changes using regex fallback")
                    return fallback_result
                except Exception as regex_error:
                    logger.error(f"Regex fallback also failed: {str(regex_error)}")
                    return {"field_updates": {}, "list_append": {}, "list_remove": {}}

        except Exception as e:
            logger.error(f"Failed to generate changes: {str(e)}")
            logger.error(f"Ticket data: {json.dumps(ticket_data, cls=DateTimeEncoder)}")
            logger.error(f"Interpreted changes: {interpreted_changes}")
            raise
