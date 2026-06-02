from rest_framework.routers import DefaultRouter

from .views import NoteViewSet, ProjectViewSet, TaskViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet)
router.register("tasks", TaskViewSet)
router.register("notes", NoteViewSet)

urlpatterns = router.urls
