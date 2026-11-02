"""Task lifecycle states persisted by :mod:`task_api`."""

from enum import StrEnum


class TaskStatus(StrEnum):
    """The native PostgreSQL enum values accepted for a task."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
