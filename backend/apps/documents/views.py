from rest_framework import generics, permissions

from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer, DocumentUploadSerializer


class DocumentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DocumentUploadSerializer
        return DocumentSerializer


class DocumentDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)
