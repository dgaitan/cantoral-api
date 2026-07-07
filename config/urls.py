from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from cc.playlists.api.views import ProfilePlaylistsView
from cc.users.api.auth_views import (
    LoginView,
    LogoutView,
    RegisterView,
    VerifyEmailTokenView,
)
from cc.users.api.profile_views import (
    FavoriteSongsView,
    ProfileView,
)
from config.views import healthcheck

urlpatterns = [
    # Health check (used by Kamal / kamal-proxy)
    path("up/", healthcheck, name="healthcheck"),
    # Django Admin
    path(settings.ADMIN_URL, admin.site.urls),
    # API
    path("api/", include("config.api_router")),
    # Email-token auth flow
    path("api/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/auth/verify", VerifyEmailTokenView.as_view(), name="auth-verify"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/refresh-token", TokenRefreshView.as_view(), name="auth-refresh"),
    # Legacy JWT endpoints (admin / tooling)
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # Songs
    path("api/v1/", include("cc.songs.api.urls")),
    # Playlists
    path("api/v1/", include("cc.playlists.api.urls")),
    # Profile
    path(
        "api/v1/profile/favorites/",
        FavoriteSongsView.as_view(),
        name="profile-favorites",
    ),
    path(
        "api/v1/profile/playlists/",
        ProfilePlaylistsView.as_view(),
        name="profile-playlists",
    ),
    path("api/v1/profile", ProfileView.as_view(), name="profile"),
    # API docs (admin-only)
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
]

if settings.DEBUG:
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
