from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class BreakdownConfig:
    """Configuration for ticket breakdown generation"""
    max_user_stories: int = 5
    max_technical_tasks: int = 3
    max_subtasks_per_story: int = 4
    max_subtasks_per_tech_task: int = 3
    min_story_points: int = 1
    max_story_points: int = 8
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BreakdownConfig':
        """Create config from dictionary, using defaults for missing values"""
        return cls(
            max_user_stories=data.get('max_user_stories', cls.max_user_stories),
            max_technical_tasks=data.get('max_technical_tasks', cls.max_technical_tasks),
            max_subtasks_per_story=data.get('max_subtasks_per_story', cls.max_subtasks_per_story),
            max_subtasks_per_tech_task=data.get('max_subtasks_per_tech_task', cls.max_subtasks_per_tech_task),
            min_story_points=data.get('min_story_points', cls.min_story_points),
            max_story_points=data.get('max_story_points', cls.max_story_points)
        )

    def to_prompt_constraints(self) -> str:
        """Convert config to prompt constraints text"""
        return f"""
        Constraints:
        - Create no more than {self.max_user_stories} user stories
        - Create no more than {self.max_technical_tasks} technical tasks
        - Each user story should have {self.max_subtasks_per_story} or fewer subtasks
        - Each technical task should have {self.max_subtasks_per_tech_task} or fewer subtasks
        - Story points should be between {self.min_story_points} and {self.max_story_points}
        """ 