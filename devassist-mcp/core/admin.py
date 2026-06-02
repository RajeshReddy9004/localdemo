from django.contrib import admin

from .models import Note, Project, Task


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "priority", "project", "due_date", "created_at")
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "description")


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "tags", "created_at")
    search_fields = ("title", "content", "tags")
