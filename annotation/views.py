from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import AnnotationImage, Polygon
from .serializers import AnnotationImageSerializer, PolygonSerializer


class AnnotationImageViewSet(viewsets.ModelViewSet):
    serializer_class = AnnotationImageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return AnnotationImage.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PolygonViewSet(viewsets.ModelViewSet):
    serializer_class = PolygonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Always scope to the requesting user's polygons. Only the list/create
        # routes carry an image_id in the URL; the detail routes (patch/delete
        # via /polygons/<pk>/) do not, so filter by it only when present.
        queryset = Polygon.objects.filter(image__user=self.request.user)
        image_id = self.kwargs.get('image_id')
        if image_id is not None:
            queryset = queryset.filter(image_id=image_id)
        return queryset

    def create(self, request, *args, **kwargs):
        image_id = kwargs.get('image_id')
        image = AnnotationImage.objects.filter(user=request.user, id=image_id).first()
        if image is None:
            return Response({'detail': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(image=image)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
