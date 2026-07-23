from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_collection, name="collection"),
    path("<uuid:document_id>/", views.document_detail, name="detail"),
    path("<uuid:document_id>/download/", views.document_download, name="download"),
]
