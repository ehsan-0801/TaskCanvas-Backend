from rest_framework import serializers

from .models import Tag, Task


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class TaskSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "due_date",
            "order",
            "tags",
            "tag_ids",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        tag_ids = validated_data.pop("tag_ids", [])
        task = Task.objects.create(**validated_data)
        task.tags.set(tag_ids)
        return task

    def update(self, instance, validated_data):
        tag_ids = validated_data.pop("tag_ids", None)
        task = super().update(instance, validated_data)
        if tag_ids is not None:
            task.tags.set(tag_ids)
        return task
