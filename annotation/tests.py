import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from .models import AnnotationImage, Polygon

# Write uploads to a throwaway dir so tests never touch the real media folder.
MEDIA_ROOT = tempfile.mkdtemp()


def make_png(width=120, height=80, color=(255, 0, 0)):
    """Return an in-memory PNG upload of a known size."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("test.png", buffer.read(), content_type="image/png")


# Force local filesystem storage during tests so uploads never touch the real
# Cloudinary account, even though the dev .env has Cloudinary credentials set.
@override_settings(
    MEDIA_ROOT=MEDIA_ROOT,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class AnnotationApiTestCase(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password="secretpass123"
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password="secretpass123"
        )

    def auth(self, user):
        self.client.force_authenticate(user=user)


class ImageUploadTests(AnnotationApiTestCase):
    def test_requires_authentication(self):
        response = self.client.get("/api/images/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_extracts_dimensions(self):
        self.auth(self.alice)
        response = self.client.post(
            "/api/images/",
            {"file": make_png(width=200, height=150)},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["width"], 200)
        self.assertEqual(response.data["height"], 150)

    def test_upload_without_file_fails(self):
        self.auth(self.alice)
        response = self.client.post("/api/images/", {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_returns_own_images(self):
        AnnotationImage.objects.create(user=self.bob, width=10, height=10)
        self.auth(self.alice)
        response = self.client.get("/api/images/")
        self.assertEqual(response.data["count"], 0)

    def test_delete_cascades_to_polygons(self):
        image = AnnotationImage.objects.create(user=self.alice, width=10, height=10)
        Polygon.objects.create(image=image, points=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]])
        self.auth(self.alice)
        response = self.client.delete(f"/api/images/{image.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Polygon.objects.filter(image=image).exists())

    def test_cannot_delete_another_users_image(self):
        image = AnnotationImage.objects.create(user=self.bob, width=10, height=10)
        self.auth(self.alice)
        response = self.client.delete(f"/api/images/{image.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PolygonTests(AnnotationApiTestCase):
    def setUp(self):
        super().setUp()
        self.image = AnnotationImage.objects.create(user=self.alice, width=100, height=100)

    def test_create_polygon(self):
        self.auth(self.alice)
        response = self.client.post(
            f"/api/images/{self.image.id}/polygons/",
            {"points": [[0.1, 0.1], [0.5, 0.2], [0.3, 0.6]], "color": "#22d3ee"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["points"]), 3)
        self.assertEqual(response.data["color"], "#22d3ee")

    def test_cannot_create_polygon_on_another_users_image(self):
        bob_image = AnnotationImage.objects.create(user=self.bob, width=10, height=10)
        self.auth(self.alice)
        response = self.client.post(
            f"/api/images/{bob_image.id}/polygons/",
            {"points": [[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_polygons_for_image(self):
        Polygon.objects.create(image=self.image, points=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]])
        self.auth(self.alice)
        response = self.client.get(f"/api/images/{self.image.id}/polygons/")
        self.assertEqual(response.data["count"], 1)

    def test_patch_polygon_label_and_color(self):
        polygon = Polygon.objects.create(
            image=self.image, points=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]]
        )
        self.auth(self.alice)
        response = self.client.patch(
            f"/api/images/polygons/{polygon.id}/",
            {"label": "cat", "color": "#16a34a"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        polygon.refresh_from_db()
        self.assertEqual(polygon.label, "cat")
        self.assertEqual(polygon.color, "#16a34a")

    def test_patch_polygon_points(self):
        polygon = Polygon.objects.create(
            image=self.image, points=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]]
        )
        self.auth(self.alice)
        new_points = [[0.15, 0.12], [0.42, 0.1], [0.25, 0.45]]
        response = self.client.patch(
            f"/api/images/polygons/{polygon.id}/",
            {"points": new_points},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        polygon.refresh_from_db()
        self.assertEqual(polygon.points, new_points)

    def test_cannot_patch_another_users_polygon(self):
        bob_image = AnnotationImage.objects.create(user=self.bob, width=10, height=10)
        polygon = Polygon.objects.create(
            image=bob_image, points=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]]
        )
        self.auth(self.alice)
        response = self.client.patch(
            f"/api/images/polygons/{polygon.id}/", {"label": "hax"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_polygon(self):
        polygon = Polygon.objects.create(
            image=self.image, points=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.1]]
        )
        self.auth(self.alice)
        response = self.client.delete(f"/api/images/polygons/{polygon.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Polygon.objects.filter(id=polygon.id).exists())
