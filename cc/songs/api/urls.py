from rest_framework.routers import SimpleRouter

from cc.songs.api.views import SongViewSet

router = SimpleRouter()
router.register("songs", SongViewSet, basename="song")

urlpatterns = router.urls
