from django.urls import path

from .views import TagViewSet, TaskViewSet

urlpatterns = [
    path("", TaskViewSet.as_view({"get": "list", "post": "create"}), name="task-list"),
    path("<int:pk>/", TaskViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="task-detail"),
    path("reorder/", TaskViewSet.as_view({"post": "reorder"}), name="task-reorder"),
    path("tags/", TagViewSet.as_view({"get": "list", "post": "create"}), name="tag-list"),
]
