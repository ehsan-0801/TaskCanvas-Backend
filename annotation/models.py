from django.conf import settings
from django.db import models


def annotation_upload_to(instance, filename):
    """Place uploads under the configured Cloudinary folder (if any).

    django-cloudinary-storage uses this path as the asset's public id, so the
    folder prefix here is what groups the images inside Cloudinary.
    """
    folder = getattr(settings, 'CLOUDINARY_FOLDER', '') or ''
    base = f'annotations/{filename}'
    return f'{folder}/{base}' if folder else base


class AnnotationImage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='annotation_images')
    file = models.ImageField(upload_to=annotation_upload_to)
    width = models.IntegerField(default=0)
    height = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.file.name


class Polygon(models.Model):
    image = models.ForeignKey(AnnotationImage, on_delete=models.CASCADE, related_name='polygons')
    label = models.CharField(max_length=100, blank=True, default='')
    color = models.CharField(max_length=20, default='#4f46e5')
    points = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Polygon {self.id}'
