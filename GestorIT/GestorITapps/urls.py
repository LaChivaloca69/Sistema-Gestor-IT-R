from django.urls import path

from .views import HomeView, ModelCreateView, ModelDeleteView, ModelListView, ModelUpdateView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("<slug:model_slug>/", ModelListView.as_view(), name="modelo-list"),
    path("<slug:model_slug>/nuevo/", ModelCreateView.as_view(), name="modelo-create"),
    path("<slug:model_slug>/<int:pk>/editar/", ModelUpdateView.as_view(), name="modelo-update"),
    path("<slug:model_slug>/<int:pk>/eliminar/", ModelDeleteView.as_view(), name="modelo-delete"),
]
