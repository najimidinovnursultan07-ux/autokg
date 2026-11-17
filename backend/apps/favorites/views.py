from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import ModelViewSet

from .models import Favorite
from .serializers import FavoriteSerializer


class FavoritePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class FavoriteViewSet(ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = FavoritePagination
    http_method_names = ("get", "post", "delete", "head", "options")

    def get_queryset(self):
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related(
                "car",
                "car__owner",
                "car__model",
                "car__model__brand",
                "car__city",
            )
            .prefetch_related("car__images")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
