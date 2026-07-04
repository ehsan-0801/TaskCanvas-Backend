from PIL import Image
from rest_framework import serializers

from .models import AnnotationImage, Polygon


class PolygonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Polygon
        fields = ["id", "label", "color", "points", "created_at"]
        read_only_fields = ["id", "created_at"]


class AnnotationImageSerializer(serializers.ModelSerializer):
    polygons = PolygonSerializer(many=True, read_only=True)

    class Meta:
        model = AnnotationImage
        fields = ["id", "file", "width", "height", "uploaded_at", "polygons"]
        read_only_fields = ["id", "width", "height", "uploaded_at", "polygons"]

    def create(self, validated_data):
        image_file = validated_data.get("file")
        # Read dimensions from the upload BEFORE saving — once the file is handed
        # to the storage backend (Cloudinary) its stream may be consumed.
        width = height = 0
        if image_file:
            try:
                image_file.seek(0)
                with Image.open(image_file) as img:
                    width, height = img.size
            finally:
                image_file.seek(0)

        validated_data["width"] = width
        validated_data["height"] = height
        return AnnotationImage.objects.create(**validated_data)
