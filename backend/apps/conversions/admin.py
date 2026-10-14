from django.contrib import admin

from apps.conversions.models import Artifact, ConversionJob, QualityReportRecord

admin.site.register(ConversionJob)
admin.site.register(Artifact)
admin.site.register(QualityReportRecord)
