from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    ENABLE_CODE_BLOCK_GENERATION: bool = True  # Tested
    ENABLE_GHERKIN_SCENARIOS: bool = True  # Tested
    ENABLE_RESEARCH_TASKS: bool = True  # Tested
    ENABLE_IMPLEMENTATION_APPROACH: bool = True  # Tested
    ENABLE_TEST_PLANS: bool = True  # Tested

    class Config:
        env_prefix = "JIRA_TOOL_"  # Environment variables should be prefixed with JIRA_TOOL_


settings = Settings()
