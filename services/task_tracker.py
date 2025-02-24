from dataclasses import dataclass, field
from typing import Dict, List, Any

from loguru import logger


@dataclass
class TaskTracker:
    """Tracks tasks generated during epic breakdown process"""
    epic_key: str
    user_stories: List[Dict[str, Any]] = field(default_factory=list)
    technical_tasks: List[Dict[str, Any]] = field(default_factory=list)
    subtasks: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def add_user_story(self, story: Dict[str, Any]) -> None:
        """Add a user story and log it"""
        self.user_stories.append(story)
        logger.debug(
            f"Added user story: {story.get('title', story.get('name', 'Unnamed'))} (Total: {len(self.user_stories)})")

    def add_technical_task(self, task: Dict[str, Any]) -> None:
        """Add a technical task and log it"""
        self.technical_tasks.append(task)
        logger.debug(
            f"Added technical task: {task.get('title', task.get('name', 'Unnamed'))} (Total: {len(self.technical_tasks)})")

    def add_subtasks(self, parent_task_title: str, subtasks: List[Dict[str, Any]]) -> None:
        """Add subtasks for a parent task and log them"""
        self.subtasks[parent_task_title] = subtasks
        logger.debug(f"Added {len(subtasks)} subtasks for {parent_task_title}")

    def get_summary(self) -> Dict[str, Any]:
        """Get current summary of all tasks"""
        return {
            "user_stories": len(self.user_stories),
            "technical_tasks": len(self.technical_tasks),
            "subtasks": sum(len(tasks) for tasks in self.subtasks.values()),
            "subtasks_by_parent": {
                parent: len(tasks) for parent, tasks in self.subtasks.items()
            }
        }

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks in structured format"""
        all_tasks = []

        # Debug log current state
        logger.debug(f"TaskTracker state before get_all_tasks:")
        logger.debug(f"User Stories: {len(self.user_stories)}")
        logger.debug(f"Technical Tasks: {len(self.technical_tasks)}")

        # Add user stories with their subtasks
        for story in self.user_stories:
            story_title = story.get('title', story.get('name', 'Unnamed'))
            logger.debug(f"Adding user story: {story_title}")
            all_tasks.append({
                "high_level_task": story,
                "subtasks": self.subtasks.get(story_title, [])
            })

        # Add technical tasks with their subtasks
        for task in self.technical_tasks:
            task_title = task.get('title', task.get('name', 'Unnamed'))
            logger.debug(f"Adding technical task: {task_title}")
            all_tasks.append({
                "high_level_task": task,
                "subtasks": self.subtasks.get(task_title, [])
            })

        logger.debug(f"Total tasks returned: {len(all_tasks)}")
        return all_tasks

    def debug_state(self) -> str:
        """Get a detailed debug representation of current state"""
        state = (
            f"TaskTracker State for {self.epic_key}:\n"
            f"User Stories ({len(self.user_stories)}):\n"
        )

        for story in self.user_stories:
            state += f"- {story.get('title', story.get('name', 'Unnamed'))}\n"

        state += f"\nTechnical Tasks ({len(self.technical_tasks)}):\n"
        for task in self.technical_tasks:
            state += f"- {task.get('title', task.get('name', 'Unnamed'))}\n"

        state += f"\nSubtasks by Parent ({len(self.subtasks)}):\n"
        for parent, subtasks in self.subtasks.items():
            state += f"- {parent}: {len(subtasks)} subtasks\n"

        return state

    def update_task_dependencies(self, task_title: str, resolved_dependencies: List[str]) -> None:
        """
        Update the dependencies of a task with resolved IDs.
        
        Args:
            task_title: Title of the task to update
            resolved_dependencies: List of resolved dependency IDs
        """
        # Update in user stories
        for story in self.user_stories:
            if story.get('title', story.get('name', '')) == task_title:
                story["dependencies"] = resolved_dependencies
                return

        # Update in technical tasks
        for task in self.technical_tasks:
            if task.get('title', task.get('name', '')) == task_title:
                task["dependencies"] = resolved_dependencies
                return
