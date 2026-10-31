from rest_framework.routers import DefaultRouter

from apps.catalog.views import ProductViewSet, TaxViewSet, VariantViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("variants", VariantViewSet, basename="variant")
router.register("taxes", TaxViewSet, basename="tax")

urlpatterns = router.urls
