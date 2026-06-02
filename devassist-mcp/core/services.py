"""
Business logic for DevAssist.

This module is the single source of truth for *what the app can do*. Both the
Django REST API (``core/views.py``) and the MCP server (``mcp_server/server.py``)
call into these functions, so the AI and the HTTP API can never drift apart.

Every function returns plain ``dict``/``list`` data (not ORM objects). That
keeps the MCP layer simple and avoids touching the database lazily from inside
an async event loop.
"""
from __future__ import annotations

from typing import Any, Optional

from django.db.models import Q

from .models import Note, Project, Task


# --------------------------------------------------------------------------- #
# Serialization helpers
# --------------------------------------------------------------------------- #
def task_to_dict(task: Task) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "project": task.project.name if task.project else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "created_at": task.created_at.isoformat(),
    }


def note_to_dict(note: Note) -> dict[str, Any]:
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "tags": [t.strip() for t in note.tags.split(",") if t.strip()],
        "created_at": note.created_at.isoformat(),
    }


def project_to_dict(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "task_count": project.tasks.count(),
    }


# --------------------------------------------------------------------------- #
# Tasks
# --------------------------------------------------------------------------- #
def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    project_name: Optional[str] = None,
    due_date: Optional[str] = None,
) -> dict[str, Any]:
    project = None
    if project_name:
        project, _ = Project.objects.get_or_create(name=project_name)
    task = Task.objects.create(
        title=title,
        description=description,
        priority=priority,
        project=project,
        due_date=due_date or None,
    )
    return task_to_dict(task)


def list_tasks(
    status: Optional[str] = None, project_name: Optional[str] = None
) -> list[dict[str, Any]]:
    qs = Task.objects.select_related("project").all()
    if status:
        qs = qs.filter(status=status)
    if project_name:
        qs = qs.filter(project__name=project_name)
    return [task_to_dict(t) for t in qs]


def get_task(task_id: int) -> Optional[dict[str, Any]]:
    task = Task.objects.select_related("project").filter(id=task_id).first()
    return task_to_dict(task) if task else None


def update_task(task_id: int, **fields: Any) -> Optional[dict[str, Any]]:
    task = Task.objects.filter(id=task_id).first()
    if not task:
        return None
    allowed = {"title", "description", "status", "priority", "due_date"}
    for key, value in fields.items():
        if key in allowed and value is not None:
            setattr(task, key, value)
    task.save()
    return task_to_dict(task)


def complete_task(task_id: int) -> Optional[dict[str, Any]]:
    return update_task(task_id, status=Task.Status.DONE)


def delete_task(task_id: int) -> bool:
    deleted, _ = Task.objects.filter(id=task_id).delete()
    return deleted > 0


# --------------------------------------------------------------------------- #
# Notes
# --------------------------------------------------------------------------- #
def create_note(title: str, content: str, tags: str = "") -> dict[str, Any]:
    note = Note.objects.create(title=title, content=content, tags=tags)
    return note_to_dict(note)


def list_notes() -> list[dict[str, Any]]:
    return [note_to_dict(n) for n in Note.objects.all()]


def get_note(note_id: int) -> Optional[dict[str, Any]]:
    note = Note.objects.filter(id=note_id).first()
    return note_to_dict(note) if note else None


def search_notes(query: str) -> list[dict[str, Any]]:
    qs = Note.objects.filter(
        Q(title__icontains=query)
        | Q(content__icontains=query)
        | Q(tags__icontains=query)
    )
    return [note_to_dict(n) for n in qs]


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #
def list_projects() -> list[dict[str, Any]]:
    return [project_to_dict(p) for p in Project.objects.all()]
