from rest_framework.routers import SimpleRouter

from cc.songs.api.views import AuthorViewSet
from cc.songs.api.views import SongViewSet

router = SimpleRouter()
router.register("songs", SongViewSet, basename="song")
router.register("authors", AuthorViewSet, basename="author")

urlpatterns = router.urls
