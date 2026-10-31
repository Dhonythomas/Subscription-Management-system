from rest_framework.routers import SimpleRouter

from apps.discounts.views import DiscountViewSet

router = SimpleRouter()
router.register("", DiscountViewSet, basename="discount")

urlpatterns = router.urls
