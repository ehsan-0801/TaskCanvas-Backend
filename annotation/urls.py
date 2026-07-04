from django.urls import path

from .views import AnnotationImageViewSet, PolygonViewSet

urlpatterns = [
    path("", AnnotationImageViewSet.as_view({"get": "list", "post": "create"}), name="image-list"),
    path("<int:pk>/", AnnotationImageViewSet.as_view({"get": "retrieve", "delete": "destroy"}), name="image-detail"),
    path("<int:image_id>/polygons/", PolygonViewSet.as_view({"get": "list", "post": "create"}), name="polygon-list"),
    path("polygons/<int:pk>/", PolygonViewSet.as_view({"patch": "partial_update", "delete": "destroy"}), name="polygon-detail"),
]
