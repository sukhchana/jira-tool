import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import uuid
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass

from loguru import logger

from config.approved_services import AWS_APPROVED_SERVICES, GCP_APPROVED_SERVICES
from jira_integration.jira_service import JiraService
from models.architecture_design import DiagramInfo, ArchitectureDesignResponse
from models.jira_ticket_details import JiraTicketDetails
from prompts.architecture_prompts import (
    ARCHITECTURE_OVERVIEW_TEMPLATE,
    ARCHITECTURE_DIAGRAM_TEMPLATES,
    SEQUENCE_DIAGRAM_TEMPLATE, 
    DIAGRAM_ANALYSIS_TEMPLATE,
    DIAGRAM_TEMPLATES,
    get_architecture_diagram_template
)
from services.execution_log_service import ExecutionLogService
from llm.vertexllm import VertexLLM
from llm.genaillm import GenAILLM
from services.mongodb_service import MongoDBService

class ArchitectureDesignService:
    """
    Service for generating architecture designs for JIRA epics.
    
    This service uses LLM to analyze JIRA epic details and generate architecture designs
    including various types of mermaid diagrams.
    """
    
    def __init__(self, execution_id: str = None):
        """
        Initialize the architecture design service.
        
        Args:
            execution_id: Optional execution ID. If not provided, a new one will be generated.
        """
        self.execution_id = execution_id or str(uuid.uuid4())
        
        # Choose LLM implementation based on model version
        model_version = os.getenv('VERTEX_MODEL_VERSION', 'gemini-1.5-pro')
        if "gemini-2.0" in model_version:
            logger.info(f"Using GenAILLM with model {model_version} for Google Search grounding")
            self.llm = GenAILLM()
        else:
            logger.info(f"Using VertexLLM with model {model_version}")
            self.llm = VertexLLM()
            
        self.jira = JiraService()
        self.execution_log = None  # Will be initialized when we have the epic_key
        self.architectures_dir = Path("architectures")
        self.architectures_dir.mkdir(exist_ok=True)
        self.execution_plans_dir = Path("execution_plans")
        self.execution_plans_dir.mkdir(exist_ok=True)
        
    async def generate_architecture_design(
        self, 
        epic_key: str, 
        cloud_provider: str, 
        additional_context: str = None
    ) -> ArchitectureDesignResponse:
        """
        Generate architecture design for a JIRA epic.
        
        Args:
            epic_key: JIRA epic key
            cloud_provider: Cloud provider (AWS or GCP)
            additional_context: Additional context for the architecture design
            
        Returns:
            Architecture design response
            
        Raises:
            ValueError: If cloud_provider is not AWS or GCP
            Exception: If epic details cannot be retrieved or architecture generation fails
        """
        logger.info(f"Generating architecture design for epic {epic_key} with {cloud_provider}")
        
        # Initialize execution log with epic_key
        self.execution_log = ExecutionLogService(epic_key=epic_key)
        
        # Validate cloud provider
        if cloud_provider.upper() not in ["AWS", "GCP"]:
            raise ValueError("Cloud provider must be either AWS or GCP")
        
        # Get epic details from JIRA
        epic_details = await self.jira.get_ticket(epic_key)
        if not epic_details:
            raise ValueError(f"Epic {epic_key} not found")
        
        # Get approved services list
        approved_services = AWS_APPROVED_SERVICES if cloud_provider.upper() == "AWS" else GCP_APPROVED_SERVICES
        
        # Generate architecture design
        try:
            # Create execution record in MongoDB
            await self.execution_log.create_execution_record(
                execution_id=self.execution_id,
                epic_key=epic_key,
                execution_plan_file=self.execution_log.filename,
                proposed_plan_file="",  # No proposed plan for architecture design
                status="IN_PROGRESS"
            )
            
            architecture_design = await self._generate_architecture_design(
                epic_details=epic_details,
                cloud_provider=cloud_provider,
                approved_services=approved_services,
                additional_context=additional_context
            )
            
            # Save the architecture design to a file
            architecture_file_path = await self._save_architecture_design(
                epic_key=epic_key,
                cloud_provider=cloud_provider,
                architecture_design=architecture_design
            )
            
            # Log execution plan
            await self._log_execution_plan(
                epic_key=epic_key,
                cloud_provider=cloud_provider,
                architecture_design=architecture_design
            )
            
            # Update execution record status
            mongodb = MongoDBService()
            mongodb.update_execution_status(self.execution_id, "COMPLETED")
            
            # Create response
            response = ArchitectureDesignResponse(
                execution_id=self.execution_id,
                epic_key=epic_key,
                cloud_provider=cloud_provider,
                architecture_overview=architecture_design["overview"],
                diagrams=architecture_design["diagrams"],
                architecture_file_path=str(architecture_file_path)
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate architecture design for epic {epic_key}: {str(e)}")
            raise Exception(f"Failed to generate architecture design: {str(e)}")
    
    async def _generate_architecture_design(
        self, 
        epic_details: JiraTicketDetails, 
        cloud_provider: str,
        approved_services: List[str],
        additional_context: str = None
    ) -> Dict[str, Any]:
        """
        Generate architecture design using LLM.
        
        Args:
            epic_details: JIRA epic details
            cloud_provider: Cloud provider (AWS or GCP)
            approved_services: List of approved services
            additional_context: Additional context for the architecture design
            
        Returns:
            Dictionary containing architecture design details
        """
        logger.info(f"Generating architecture design for epic {epic_details.key}")
        
        # Log the architecture design request
        self.execution_log.log_section(
            "Architecture Design Request",
            f"Generating architecture design for {epic_details.key} using {cloud_provider}\n\n"
            f"Epic Summary: {epic_details.summary}\n\n"
            f"Additional Context: {additional_context or 'None provided'}"
        )
        
        # Call the LLM with web search capability
        model_version = os.getenv('VERTEX_MODEL_VERSION', 'gemini-1.5-pro')
        logger.info(f"Generating architecture design using model: {model_version}")
        
        # Prepare common parameters for prompt templates
        approved_services_str = ", ".join(approved_services)
        context_params = {
            "epic_title": epic_details.summary,
            "epic_description": epic_details.description,
            "cloud_provider": cloud_provider,
            "approved_services": approved_services_str,
            "additional_context": additional_context or "No additional context provided."
        }
        
        # Step 1: Generate the architecture overview
        logger.info("Step 1: Generating architecture overview")
        overview_prompt = ARCHITECTURE_OVERVIEW_TEMPLATE.format(**context_params)
        
        overview = await self.llm.generate_content_with_search(
            prompt=overview_prompt, 
            temperature=0.2
        )
        
        self.execution_log.log_llm_interaction(
            stage="Architecture Overview Generation",
            prompt=overview_prompt,
            response=overview,
            parsed_result=None
        )
        
        # Step 2: Generate the architecture-beta diagram
        logger.info("Step 2: Generating architecture-beta diagram")
        
        # Get the appropriate template for the cloud provider
        architecture_template = get_architecture_diagram_template(cloud_provider)
        architecture_prompt = architecture_template.format(**context_params)
        
        architecture_response = await self.llm.generate_content_with_search(
            prompt=architecture_prompt, 
            temperature=0.2
        )
        
        self.execution_log.log_llm_interaction(
            stage="Architecture Diagram Generation",
            prompt=architecture_prompt,
            response=architecture_response,
            parsed_result=None
        )
        
        # Step 3: Generate sequence diagrams
        logger.info("Step 3: Generating sequence diagrams")
        sequence_prompt = SEQUENCE_DIAGRAM_TEMPLATE.format(**context_params)
        
        sequence_response = await self.llm.generate_content_with_search(
            prompt=sequence_prompt, 
            temperature=0.2
        )
        
        self.execution_log.log_llm_interaction(
            stage="Sequence Diagram Generation",
            prompt=sequence_prompt,
            response=sequence_response,
            parsed_result=None
        )
        
        # Step 4: Analyze which specialized diagrams would be most useful
        logger.info("Step 4: Analyzing which specialized diagrams would be useful")
        analysis_prompt = DIAGRAM_ANALYSIS_TEMPLATE.format(**context_params)
        
        analysis_response = await self.llm.generate_content_with_search(
            prompt=analysis_prompt, 
            temperature=0.2
        )
        
        self.execution_log.log_llm_interaction(
            stage="Diagram Analysis",
            prompt=analysis_prompt,
            response=analysis_response,
            parsed_result=None
        )
        
        # Parse the analysis to determine which diagrams to generate
        diagram_types = []
        for line in analysis_response.strip().split('\n'):
            if ':' in line and any(dt in line.lower() for dt in DIAGRAM_TEMPLATES.keys()):
                for diagram_type in DIAGRAM_TEMPLATES.keys():
                    if diagram_type in line.lower():
                        diagram_types.append(diagram_type)
                        break
        
        # Generate up to 3 diagram types
        diagram_types = list(set(diagram_types))[:3]  # Remove duplicates and limit to 3
        logger.info(f"Generating {len(diagram_types)} specialized diagrams: {diagram_types}")
        
        # Initialize the diagrams list with architecture and sequence diagrams
        diagrams = []
        
        # Parse architecture diagram
        architecture_diagram = self._parse_diagram_from_text(architecture_response, "architecture")
        if architecture_diagram:
            diagrams.append(architecture_diagram)
            
        # Parse sequence diagram
        sequence_diagram = self._parse_diagram_from_text(sequence_response, "sequence")
        if sequence_diagram:
            diagrams.append(sequence_diagram)
        
        # Step 5: Generate specialized diagrams based on the analysis
        for diagram_type in diagram_types:
            logger.info(f"Generating {diagram_type} diagram")
            
            # Get the appropriate template for this diagram type
            diagram_template = DIAGRAM_TEMPLATES.get(diagram_type)
            if not diagram_template:
                logger.warning(f"No template found for diagram type: {diagram_type}")
                continue
                
            # Format the prompt with context parameters
            diagram_prompt = diagram_template.format(**context_params)
            
            # Generate the diagram
            diagram_response = await self.llm.generate_content_with_search(
                prompt=diagram_prompt, 
                temperature=0.3
            )
            
            self.execution_log.log_llm_interaction(
                stage=f"{diagram_type.capitalize()} Diagram Generation",
                prompt=diagram_prompt,
                response=diagram_response,
                parsed_result=None
            )
            
            # Parse the diagram
            diagram = self._parse_diagram_from_text(diagram_response, diagram_type)
            if diagram:
                diagrams.append(diagram)
        
        # Return the architecture design data
        architecture_design = {
            "overview": overview,
            "diagrams": diagrams
        }
        
        return architecture_design
    
    async def _save_architecture_design(
        self, 
        epic_key: str, 
        cloud_provider: str, 
        architecture_design: Dict[str, Any]
    ) -> Path:
        """
        Save the architecture design to a markdown file.
        
        Args:
            epic_key: JIRA epic key
            cloud_provider: Cloud provider
            architecture_design: Architecture design dictionary
            
        Returns:
            Path to the saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ARCHITECTURE_{epic_key}_{cloud_provider}_{timestamp}.md"
        filepath = self.architectures_dir / filename
        
        with open(filepath, "w") as f:
            f.write(f"# Architecture Design for {epic_key}\n\n")
            f.write(f"* **Cloud Provider:** {cloud_provider}\n")
            f.write(f"* **Execution ID:** {self.execution_id}\n")
            f.write(f"* **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Architecture Overview\n\n")
            f.write(architecture_design["overview"])
            f.write("\n\n")
            
            for i, diagram in enumerate(architecture_design["diagrams"]):
                f.write(f"## {diagram.title}\n\n")
                f.write(f"{diagram.mermaid_code}\n\n")
                if diagram.description:
                    f.write(f"{diagram.description}\n\n")
        
        # Log the file creation
        self.execution_log.log_section(
            "Architecture Design File",
            f"Architecture design saved to {filepath}\n\n"
            f"Contains {len(architecture_design['diagrams'])} diagrams"
        )
        
        logger.info(f"Architecture design saved to {filepath}")
        return filepath
    
    async def _log_execution_plan(
        self, 
        epic_key: str, 
        cloud_provider: str, 
        architecture_design: Dict[str, Any]
    ) -> None:
        """
        Log the execution plan to a file.
        
        Args:
            epic_key: JIRA epic key
            cloud_provider: Cloud provider
            architecture_design: Architecture design dictionary
        """
        # Create a summary of the architecture design
        diagram_summaries = []
        for i, diagram in enumerate(architecture_design["diagrams"]):
            diagram_summaries.append(
                f"### {i+1}. {diagram.title}\n"
                f"Type: {diagram.type}\n"
            )
        
        diagram_summary_text = "\n".join(diagram_summaries)
        
        # Log the architecture summary
        self.execution_log.log_section(
            "Architecture Design Summary",
            f"Generated architecture design for {epic_key} using {cloud_provider}\n\n"
            f"## Diagrams Generated\n\n{diagram_summary_text}"
        )
        
        # Log the completion summary
        self.execution_log.log_summary({
            "epic_key": epic_key,
            "cloud_provider": cloud_provider,
            "diagrams_count": len(architecture_design["diagrams"]),
            "execution_id": self.execution_id,
            "status": "COMPLETED"
        }) 

    def _parse_diagram_from_text(self, text: str, diagram_type: str) -> Optional[DiagramInfo]:
        """
        Parse a Mermaid diagram from text returned by the LLM.
        
        Args:
            text: Text containing the diagram
            diagram_type: Type of diagram (architecture, sequence, flowchart, etc.)
            
        Returns:
            DiagramInfo object or None if no diagram found
        """
        # Find sections between ```mermaid and ```
        pattern = r"```mermaid\s*([\s\S]*?)```"
        matches = re.findall(pattern, text)
        
        if not matches:
            logger.warning(f"No mermaid diagram found in the {diagram_type} response")
            return None
            
        # Use the first diagram found
        mermaid_code = matches[0].strip()
        
        # Extract title from the text before/after the diagram
        title = f"{diagram_type.capitalize()} Diagram"
        description = ""
        
        # Look for titles and descriptions in the text
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "```mermaid" in line and i > 0:
                # Check if the previous line is a heading
                for j in range(i-1, max(0, i-5), -1):
                    if lines[j].strip().startswith("#"):
                        title = lines[j].strip().replace("#", "").strip()
                        break
            
            if "```" in line and "mermaid" not in line:
                # Collect text after the diagram for description
                description_lines = []
                for j in range(i+1, min(len(lines), i+20)):
                    if "```mermaid" in lines[j]:  # Stop if another diagram starts
                        break
                    description_lines.append(lines[j])
                
                if description_lines:
                    description = "\n".join(description_lines).strip()
                    break
        
        # Create the diagram info object
        return DiagramInfo(
            title=title,
            type=diagram_type,
            mermaid_code=f"```mermaid\n{mermaid_code}\n```",
            description=description
        ) 