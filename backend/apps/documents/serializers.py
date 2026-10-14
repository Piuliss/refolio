from rest_framework import serializers

from apps.documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "original_filename",
            "mime_type",
            "size_bytes",
            "page_count",
            "language_hint",
            "created_at",
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model = Document
        fields = ["id", "file", "language_hint", "original_filename", "created_at"]
        read_only_fields = ["id", "original_filename", "created_at"]

    def validate_file(self, value):
        name = value.name.lower()
        if not name.endswith(".pdf"):
            raise serializers.ValidationError("Only PDF uploads are supported in Phase 1.")
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("File exceeds 50 MiB limit.")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        uploaded = validated_data["file"]
        return Document.objects.create(
            owner=request.user,
            original_filename=uploaded.name,
            file=uploaded,
            mime_type=uploaded.content_type or "application/pdf",
            size_bytes=uploaded.size,
            language_hint=validated_data.get("language_hint", "es"),
        )
