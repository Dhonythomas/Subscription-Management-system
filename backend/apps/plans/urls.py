from rest_framework.routers import SimpleRouter

from apps.plans.views import PlanViewSet

router = SimpleRouter()
router.register("", PlanViewSet, basename="plan")

urlpatterns = router.urls
