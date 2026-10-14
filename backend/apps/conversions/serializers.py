from rest_framework import serializers

from apps.conversions.models import Artifact, ConversionJob, QualityReportRecord


class ConversionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionJob
        fields = [
            "id",
            "document",
            "status",
            "progress_message",
            "error_message",
            "parser_name",
            "engine_version",
            "cancel_requested",
            "created_at",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields


class ArtifactSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Artifact
        fields = ["id", "kind", "download_url", "created_at"]

    def get_download_url(self, obj: Artifact) -> str:
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class QualityReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityReportRecord
        fields = ["payload"]
