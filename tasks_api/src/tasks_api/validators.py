"""Business-rule validators for task operations."""

from datetime import UTC, datetime

from tasks_api.enums import TaskStatus
from tasks_api.exceptions import ValidationException


def validate_task_title(title: str) -> None:
    """Require a non-empty task title."""

    if not title or not title.strip():
        raise ValidationException("Task title cannot be empty.")


def validate_task_status(status: str) -> TaskStatus:
    """Validate that the status is a known TaskStatus value."""

    try:
        return TaskStatus(status)
    except ValueError as err:
        valid = [s.value for s in TaskStatus]
        raise ValidationException(
            f"Invalid status '{status}'. Must be one of: {valid}"
        ) from err


def validate_due_date(due_date: datetime) -> None:
    """Validate due date business rules.

    Rules:
    - Must be timezone-aware (ISO 8601 with timezone info)
    - Must be in the future (reject past dates)
    """

    if due_date.tzinfo is None:
        raise ValidationException(
            "Due date must be timezone-aware (ISO 8601 with timezone)."
        )

    if due_date <= datetime.now(UTC):
        raise ValidationException("Due date must be in the future.")


def validate_update_payload_not_empty(**fields: object) -> None:
    """Reject an update where every field is None (empty payload)."""

    if all(value is None for value in fields.values()):
        raise ValidationException(
            "Update payload must include at least one field to update."
        )
