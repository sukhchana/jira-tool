import asyncio
import os
from pathlib import Path
from loguru import logger

from services.architecture_design_service import ArchitectureDesignService
from models.jira_ticket_details import JiraTicketDetails

# Configure logging
logger.add("test_architecture_service.log", rotation="500 MB")

class MockJiraService:
    """Mock JiraService for testing"""
    
    async def get_ticket(self, ticket_key):
        """Return a mock JiraTicketDetails"""
        from datetime import datetime
        now = datetime.now().isoformat()
        
        return JiraTicketDetails(
            key="TEST-123",
            summary="Cloud-based AI Inference Platform",
            description="""
            We need to build a scalable cloud-based platform for AI model inference with the following requirements:
            
            1. Support for high-throughput model inference
            2. Auto-scaling based on demand
            3. API Gateway for client access
            4. Monitoring and logging capabilities
            5. Cost optimization for idle periods
            6. Support for GPU acceleration
            7. Secure access control
            8. Integration with existing data pipelines
            """,
            issue_type="Epic",
            status="Open",
            created=now,
            updated=now,
            project_key="TEST",
            assignee="test.user",
            reporter="product.owner",
            priority="High",
            labels=["ai", "ml", "cloud", "inference"],
            components=["AI Platform", "Infrastructure"]
        )

# Patch the JiraService in ArchitectureDesignService
def patch_jira_service(service):
    """Replace the JiraService with our mock"""
    service.jira = MockJiraService()
    return service

async def test_architecture_design():
    """Test the architecture design service with Google Search grounding"""
    try:
        print("Testing Architecture Design Service...")
        
        # Set the environment to use Gemini 2.0 Flash
        os.environ["VERTEX_MODEL_VERSION"] = "gemini-2.0-flash"
        
        # Initialize the service
        service = ArchitectureDesignService()
        service = patch_jira_service(service)
        
        # Create the architectures directory if it doesn't exist
        Path("architectures").mkdir(exist_ok=True)
        
        # Generate architecture design
        print("\nGenerating architecture design with Google Search grounding...")
        response = await service.generate_architecture_design(
            epic_key="TEST-123",
            cloud_provider="AWS",
            additional_context="This should be optimized for machine learning workloads and integrate with existing MLOps pipelines."
        )
        
        # Print response details
        print(f"\nArchitecture design generated successfully!")
        print(f"Execution ID: {response.execution_id}")
        print(f"File path: {response.architecture_file_path}")
        print(f"Diagrams generated: {len(response.diagrams)}")
        
        print("\nArchitecture Overview:")
        print("=====================")
        print(response.architecture_overview[:500] + "..." if len(response.architecture_overview) > 500 else response.architecture_overview)
        
        print("\nDiagrams:")
        for i, diagram in enumerate(response.diagrams):
            print(f"\n{i+1}. {diagram.title} ({diagram.type})")
        
        return response
    
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        print(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    print("Starting Architecture Design Service test with Google Search grounding...")
    print("Make sure you have set these environment variables:")
    print("- GCP_PROJECT_ID")
    print("- VERTEX_LOCATION (optional, defaults to us-central1)")
    print("\nRunning test...")
    
    try:
        result = asyncio.run(test_architecture_design())
        print("\nTest completed successfully!")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {str(e)}") 