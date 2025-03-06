import asyncio
import pytest
import os
from unittest.mock import patch, MagicMock

from services.architecture_design_service import ArchitectureDesignService
from models.architecture_design import DiagramInfo

# Sample mermaid diagrams for testing
VALID_DIAGRAM = """graph TD
    A[Start] --> B{Is it valid?}
    B -->|Yes| C[Great!]
    B -->|No| D[Fix it]
    D --> B
"""

INVALID_DIAGRAM = """graph TD
    A[Start] --> B{Is it valid?
    B -->|Yes| C[Great!]
    B -->|No| D[Fix it]
    D --> B
"""

FIXED_DIAGRAM = """graph TD
    A[Start] --> B{Is it valid?}
    B -->|Yes| C[Great!]
    B -->|No| D[Fix it]
    D --> B
"""

@pytest.fixture
def mock_mermaid_cli_installed():
    """Mock that mermaid-cli is installed"""
    with patch('subprocess.run') as mock_run:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process
        yield mock_run

@pytest.fixture
def mock_mermaid_cli_not_installed():
    """Mock that mermaid-cli is not installed"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("No such file or directory: 'mmdc'")
        yield mock_run

@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    mock = MagicMock()
    mock.generate_content.return_value = f"```mermaid\n{FIXED_DIAGRAM}\n```"
    return mock

class TestMermaidValidation:
    """Tests for Mermaid diagram validation functionality"""
    
    async def test_validate_valid_diagram_with_cli(self, mock_mermaid_cli_installed):
        """Test validation of a valid diagram with mermaid-cli"""
        service = ArchitectureDesignService()
        is_valid, error = service._validate_mermaid_diagram(VALID_DIAGRAM)
        
        assert is_valid is True
        assert error is None
    
    async def test_validate_invalid_diagram_with_cli(self, mock_mermaid_cli_installed):
        """Test validation of an invalid diagram with mermaid-cli"""
        with patch('subprocess.run') as mock_run:
            # Configure the mock to indicate a validation error
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.stderr = "Syntax error in graph: missing closing curly brace"
            mock_run.return_value = mock_process
            
            service = ArchitectureDesignService()
            is_valid, error = service._validate_mermaid_diagram(INVALID_DIAGRAM)
            
            assert is_valid is False
            assert "Syntax error" in error
    
    async def test_fallback_to_python_validation(self, mock_mermaid_cli_not_installed):
        """Test fallback to Python validation when mermaid-cli is not installed"""
        service = ArchitectureDesignService()
        
        # Valid diagram
        is_valid, error = service._validate_mermaid_diagram(VALID_DIAGRAM)
        assert is_valid is True
        
        # Invalid diagram with missing bracket
        is_valid, error = service._validate_mermaid_diagram(INVALID_DIAGRAM)
        assert is_valid is False
        assert "bracket" in error.lower()
    
    async def test_fix_mermaid_diagram(self, mock_llm):
        """Test fixing an invalid Mermaid diagram via LLM"""
        service = ArchitectureDesignService()
        service.llm = mock_llm
        
        with patch.object(service, '_validate_mermaid_diagram') as mock_validate:
            # First validation fails, second succeeds
            mock_validate.side_effect = [(False, "Syntax error"), (True, None)]
            
            fixed_code = await service._fix_mermaid_diagram(
                INVALID_DIAGRAM, 
                "Syntax error", 
                "flowchart"
            )
            
            assert fixed_code == FIXED_DIAGRAM
            assert mock_llm.generate_content.called
    
    async def test_parse_diagram_with_validation(self, mock_llm):
        """Test the integration of parsing and validation"""
        service = ArchitectureDesignService()
        service.llm = mock_llm
        
        with patch.object(service, '_validate_mermaid_diagram') as mock_validate:
            # First validation fails, second succeeds
            mock_validate.side_effect = [(False, "Syntax error"), (True, None)]
            
            text = f"# Test Diagram\n\n```mermaid\n{INVALID_DIAGRAM}\n```\n\nThis is a test diagram."
            diagram_info = service._parse_diagram_from_text(text, "flowchart")
            
            assert diagram_info is not None
            assert isinstance(diagram_info, DiagramInfo)
            assert "Test Diagram" in diagram_info.title
            assert FIXED_DIAGRAM in diagram_info.mermaid_code
            
            # Verify LLM was called to fix the diagram
            assert mock_llm.generate_content.called

if __name__ == "__main__":
    # Run the tests using pytest
    pytest.main(["-xvs", __file__]) 