from rest_framework.routers import SimpleRouter

from cc.songs.api.views import AuthorViewSet
from cc.songs.api.views import SongViewSet
from cc.songs.api.views import TagViewSet

router = SimpleRouter()
router.register("songs", SongViewSet, basename="song")
router.register("authors", AuthorViewSet, basename="author")
router.register("tags", TagViewSet, basename="tag")

urlpatterns = router.urls
