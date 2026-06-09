# Report: Authors CRUD

**Spec:** `.specs/authors-crud.md`
**Date:** 2026-06-09
**Tests:** `cc/songs/tests/api/test_authors_crud.py`
**Status:** ✅ All scenarios passing

## Scenarios Implemented

| # | Scenario | Test function | Status |
|---|----------|---------------|--------|
| 1 | List all authors returns 200 with all authors | `test_list_all_authors_returns_200_with_all_authors` | ✅ |
| 2 | List authors is publicly accessible | `test_list_authors_is_publicly_accessible` | ✅ |
| 3 | Retrieve an existing author returns 200 | `test_retrieve_existing_author_returns_200` | ✅ |
| 4 | Retrieve a non-existent author returns 404 | `test_retrieve_non_existent_author_returns_404` | ✅ |
| 5 | Retrieve author is publicly accessible | `test_retrieve_author_is_publicly_accessible` | ✅ |
| 6 | Create author with all fields returns 201 | `test_create_author_with_all_fields_returns_201` | ✅ |
| 7 | Create author auto-generates slug from name | `test_create_author_auto_generates_slug_from_name` | ✅ |
| 8 | Create author with only name returns 201 | `test_create_author_with_only_name_returns_201` | ✅ |
| 9 | Create author without name returns 400 | `test_create_author_without_name_returns_400` | ✅ |
| 10 | Create author without permission returns 403 | `test_create_author_without_permission_returns_403` | ✅ |
| 11 | Create author without authentication returns 401 | `test_create_author_unauthenticated_returns_401` | ✅ |
| 12 | Retrieve author songs returns associated songs | `test_retrieve_author_songs_returns_associated_songs` | ✅ |
| 13 | Retrieve author songs empty list when no songs | `test_retrieve_author_songs_empty_list_when_no_songs` | ✅ |
| 14 | Retrieve songs for non-existent author returns 404 | `test_retrieve_songs_for_non_existent_author_returns_404` | ✅ |
| 15 | Retrieve author songs is publicly accessible | `test_retrieve_author_songs_is_publicly_accessible` | ✅ |
| 16 | Full update author returns 200 | `test_full_update_author_returns_200` | ✅ |
| 17 | Full update re-generates slug when slug omitted | `test_full_update_regenerates_slug_when_slug_omitted` | ✅ |
| 18 | Full update non-existent author returns 404 | `test_full_update_non_existent_author_returns_404` | ✅ |
| 19 | Full update without permission returns 403 | `test_full_update_without_permission_returns_403` | ✅ |
| 20 | Full update without authentication returns 401 | `test_full_update_unauthenticated_returns_401` | ✅ |
| 21 | Partial update bio only returns 200 | `test_partial_update_bio_only_returns_200` | ✅ |
| 22 | Partial update without permission returns 403 | `test_partial_update_without_permission_returns_403` | ✅ |
| 23 | Partial update without authentication returns 401 | `test_partial_update_unauthenticated_returns_401` | ✅ |
| 24 | Delete author returns 204 | `test_delete_author_returns_204` | ✅ |
| 25 | Delete non-existent author returns 404 | `test_delete_non_existent_author_returns_404` | ✅ |
| 26 | Delete without permission returns 403 | `test_delete_without_permission_returns_403` | ✅ |
| 27 | Delete without authentication returns 401 | `test_delete_unauthenticated_returns_401` | ✅ |

## Code Created / Modified

| File | What changed |
|------|--------------|
| `cc/songs/models.py` | Added `image`, `bio`, `slug` fields to `Author` |
| `cc/songs/migrations/0002_add_image_bio_slug_to_author.py` | Migration for new fields |
| `cc/songs/api/serializers.py` | Updated `AuthorSerializer` (added 3 fields); added `AuthorWriteSerializer` with slug auto-generation |
| `cc/songs/api/views.py` | Added `AuthorViewSet` with list, retrieve, create, update, partial_update, destroy, and songs action |
| `cc/songs/api/urls.py` | Registered `AuthorViewSet` at `authors/` with basename `author` |
| `cc/songs/tests/factories.py` | Added `image`, `bio`, `slug` defaults to `AuthorFactory` |
| `cc/songs/tests/api/test_authors_crud.py` | New test file — 27 scenarios |

## Decisions & Notes

- **`image` as `URLField`** — no media/upload infrastructure exists; an external URL is the simplest approach.
- **Slug auto-generation logic lives in `AuthorWriteSerializer.validate`** — distinguishes between full and partial updates via `self.partial` so a PATCH that omits `slug` never regenerates it, while a POST or PUT with a missing/empty slug always auto-generates from `name`.
- **`destroy` returns bare `Response(204)`** instead of `ApiResponse` — HTTP 204 has no body by spec; wrapping it in the envelope would be incorrect.
- **`CanCreateSongs` reused for writes** — no new permission was created; authors are directly tied to the songs workflow and the existing permission fits without introducing a new user field.
- **`songs` action uses existing `SongSerializer`** — returns the full song payload for consistency with `GET /api/v1/songs/{id}/`.

## Final Test Run

```
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.3, pluggy-1.6.0
django: version: 6.0.6, settings: config.settings.test (from option)
collected 27 items

cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_list_all_authors_returns_200_with_all_authors PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_list_authors_is_publicly_accessible PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_retrieve_existing_author_returns_200 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_retrieve_non_existent_author_returns_404 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_retrieve_author_is_publicly_accessible PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_create_author_with_all_fields_returns_201 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_create_author_auto_generates_slug_from_name PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_create_author_with_only_name_returns_201 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_create_author_without_name_returns_400 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_create_author_without_permission_returns_403 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_create_author_unauthenticated_returns_401 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_retrieve_author_songs_returns_associated_songs PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_retrieve_author_songs_empty_list_when_no_songs PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_retrieve_songs_for_non_existent_author_returns_404 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_retrieve_author_songs_is_publicly_accessible PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_full_update_author_returns_200 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_full_update_regenerates_slug_when_slug_omitted PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_full_update_non_existent_author_returns_404 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_full_update_without_permission_returns_403 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_full_update_unauthenticated_returns_401 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_partial_update_bio_only_returns_200 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_partial_update_without_permission_returns_403 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_partial_update_unauthenticated_returns_401 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_delete_author_returns_204 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_delete_non_existent_author_returns_404 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_delete_without_permission_returns_403 PASSED
cc/songs/tests/api/test_authors_crud.py::TestAuthorsCrud::test_delete_unauthenticated_returns_401 PASSED

27 passed in 0.42s

Full suite: 111 passed, 1 warning in 0.95s
```
