from django.test import TestCase

from core import services
from core.models import Note, Task


class TaskServiceTests(TestCase):
    def test_create_and_complete_task(self):
        created = services.create_task(
            title="Apply to Acme", priority="high", project_name="Job Search"
        )
        self.assertEqual(created["title"], "Apply to Acme")
        self.assertEqual(created["status"], "todo")
        self.assertEqual(created["project"], "Job Search")

        done = services.complete_task(created["id"])
        self.assertEqual(done["status"], "done")
        self.assertEqual(Task.objects.get(id=created["id"]).status, "done")

    def test_list_tasks_filters_by_status(self):
        services.create_task(title="A")
        b = services.create_task(title="B")
        services.complete_task(b["id"])

        todo = services.list_tasks(status="todo")
        self.assertEqual(len(todo), 1)
        self.assertEqual(todo[0]["title"], "A")


class NoteServiceTests(TestCase):
    def test_search_notes(self):
        services.create_note(
            title="MCP basics", content="Tools, resources, prompts", tags="mcp,ai"
        )
        services.create_note(title="Django ORM", content="QuerySets", tags="django")

        hits = services.search_notes("resources")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["title"], "MCP basics")
        self.assertEqual(Note.objects.count(), 2)
