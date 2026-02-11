"""Canonical templates for planning documents under docs/backlog.

Purpose:
    Define the repository-approved structure for planning artifacts and provide
    reusable helpers for both document generation and validation.

Relationships:
    - Used by `scripts.docs_as_code.new_task` for scaffold generation.
    - Used by `scripts.docs_as_code.validate_tasks` for structural checks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskTemplate:
    """Describes one planning-document template."""

    status: str
    sections: tuple[str, ...]
    checklist: tuple[str, ...]
    intro: str


TEMPLATES: dict[str, TaskTemplate] = {
    "programme": TaskTemplate(
        status="in_progress",
        sections=(
            "Objective",
            "Scope",
            "Delivery Model",
            "Active Epics",
            "Acceptance Criteria",
            "Checklist",
        ),
        checklist=(
            "Programme scaffold created",
            "Linked epics and stories",
            "Governance checkpoints defined",
        ),
        intro="Cross-cutting programme scope and governance are defined here.",
    ),
    "epic": TaskTemplate(
        status="proposed",
        sections=(
            "Goal",
            "In Scope",
            "Out of Scope",
            "Stories",
            "Acceptance Criteria",
            "Checklist",
        ),
        checklist=(
            "Stories linked",
            "Acceptance criteria defined",
            "Execution gate defined",
        ),
        intro="Major capability increment managed through linked stories.",
    ),
    "story": TaskTemplate(
        status="proposed",
        sections=(
            "Objective",
            "Scope",
            "Acceptance Criteria",
            "Test Requirements",
            "Done Definition",
            "Checklist",
        ),
        checklist=(
            "Implementation complete",
            "Tests and validations complete",
            "Docs synchronized",
        ),
        intro="Implementation slice with acceptance-driven scope.",
    ),
    "task": TaskTemplate(
        status="proposed",
        sections=(
            "Objective",
            "PR Scope",
            "Deliverables",
            "Acceptance Criteria",
            "Checklist",
        ),
        checklist=(
            "Implementation complete",
            "Validation complete",
            "Docs updated",
        ),
        intro="PR-sized execution unit; may be linked to a story or standalone.",
    ),
    "fix": TaskTemplate(
        status="proposed",
        sections=(
            "Context",
            "Objective",
            "Scope",
            "Acceptance Criteria",
            "Validation",
            "Checklist",
        ),
        checklist=(
            "Root cause documented",
            "Fix implemented",
            "Regression checks passed",
        ),
        intro="Focused correction of a known issue.",
    ),
    "review": TaskTemplate(
        status="pending",
        sections=(
            "Review Scope",
            "Findings",
            "Decision",
            "Follow-up Actions",
            "Checklist",
        ),
        checklist=(
            "Findings captured",
            "Decision recorded",
            "Follow-up tasks linked",
        ),
        intro="Structured review artifact for implementation or readiness checks.",
    ),
    "task-log": TaskTemplate(
        status="active",
        sections=(
            "Context",
            "Worklog",
            "Next Actions",
        ),
        checklist=(),
        intro="Rolling execution log for the active session context.",
    ),
    "reference": TaskTemplate(
        status="active",
        sections=("Purpose",),
        checklist=(),
        intro="Reference entry for planning conventions and navigation.",
    ),
}

TYPE_TO_SUBDIR: dict[str, str] = {
    "programme": "programmes",
    "epic": "epics",
    "story": "stories",
    "task": "tasks",
    "fix": "tasks",
    "review": "reviews",
    "task-log": "",
    "reference": "",
}

TYPE_TO_FILENAME_PREFIX: dict[str, str] = {
    "programme": "programme",
    "epic": "epic",
    "story": "story",
    "task": "task",
    "fix": "fix",
    "review": "review",
    "task-log": "current",
    "reference": "README",
}


def supported_types() -> tuple[str, ...]:
    """Return supported task frontmatter types in a stable order."""
    return tuple(TEMPLATES.keys())


def subdirectory_for(task_type: str) -> str:
    """Return backlog subdirectory for a task type."""
    return TYPE_TO_SUBDIR[task_type]


def filename_prefix_for(task_type: str) -> str:
    """Return canonical filename prefix for a task type."""
    return TYPE_TO_FILENAME_PREFIX[task_type]


def invalid_title_prefixes() -> tuple[str, ...]:
    """Return disallowed title/H1 prefixes that duplicate frontmatter type context."""
    return ("programme ", "program ", "epic ", "story ", "task ", "review ", "fix ")
