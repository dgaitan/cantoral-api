from rest_framework.routers import SimpleRouter

from cc.songs.api.views import AuthorViewSet, SongViewSet, TagViewSet

router = SimpleRouter()
router.register("songs", SongViewSet, basename="song")
router.register("authors", AuthorViewSet, basename="author")
router.register("tags", TagViewSet, basename="tag")

urlpatterns = router.urls
