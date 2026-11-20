import logging

from django.db import OperationalError, connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_503_SERVICE_UNAVAILABLE
from rest_framework.views import APIView


logger = logging.getLogger(__name__)


class ApiRootView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "message": "AutoBuy API",
            "version": "1.0",
            "status": "ok",
            "docs": {
                "health": "/api/health/",
                "auth": "/api/auth/",
                "cars": "/api/cars/",
                "favorites": "/api/favorites/",
                "admin": "/api/admin/",
            },
        })


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class ReadinessCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            connection.ensure_connection()
        except OperationalError:
            logger.exception("Database readiness check failed")
            return Response(
                {"status": "unavailable", "service": "database"},
                status=HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ready", "database": "ok"})
