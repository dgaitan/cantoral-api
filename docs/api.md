# Cantoral Católico — API Reference

Base URL: `https://api.cantoralcatolico.org` (production) · `http://localhost:8000` (local dev)

All endpoints return a JSON envelope:

```json
{
  "success": true | false,
  "data": { ... } | {},
  "errors": [],
  "message": ""
}
```

All list endpoints return a paginated envelope inside `data`:

```json
{
  "data": {
    "count": 100,
    "next": "http://.../api/v1/songs/?page=2",
    "previous": null,
    "results": [...]
  }
}
```

**Page size:** 20 items per page. Use `?page=N` to navigate.

**Search:** All list endpoints accept `?search=<query>`. Songs use a mixed strategy: PostgreSQL full-text search on song name and lyrics (type full words for best results), and case-insensitive substring matching on author and tag names (partial words work). Authors and tags use full-text search on their own fields.

---

## Authentication

Auth endpoints do not require a token. All other requests that need authentication must include:

```
Authorization: Bearer <access_token>
```

---

### POST /api/auth/register

Register a new user. Sends a one-time email verification code.

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "strongpassword",
  "name": "Full Name"
}
```

**Response 201:**
```json
{
  "success": true,
  "data": {},
  "errors": [],
  "message": "Check your email inbox and use the code to log in."
}
```

**Response 400:** Validation errors (e.g., email already registered, weak password).

---

### POST /api/auth/login

Request a one-time email login code for an existing account.

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "strongpassword"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {},
  "errors": [],
  "message": "If credentials are correct, check your email for a login code."
}
```

---

### POST /api/auth/verify

Exchange the email verification code for JWT tokens.

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com",
  "token": "123456"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "access_token": "<jwt>",
    "refresh_token": "<jwt>"
  },
  "errors": [],
  "message": "Email successfully verified."
}
```

**Response 400:** Invalid or expired token.

---

### POST /api/auth/logout

Blacklist the refresh token (invalidates the session).

**Auth required:** Yes (access token)

**Request body:**
```json
{
  "refresh_token": "<jwt>"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {},
  "errors": [],
  "message": "Successfully logged out."
}
```

---

### POST /api/auth/refresh-token

Rotate the refresh token and get a new access token.

**Auth required:** No

**Request body:**
```json
{
  "refresh": "<refresh_jwt>"
}
```

**Response 200:**
```json
{
  "access": "<new_access_jwt>",
  "refresh": "<new_refresh_jwt>"
}
```

---

## Profile

### GET /api/v1/profile

Get the authenticated user's profile.

**Auth required:** Yes

**Response 200:**
```json
{
  "success": true,
  "data": {
    "email": "user@example.com",
    "name": "Full Name"
  }
}
```

---

### PUT /api/v1/profile

Update the authenticated user's profile (partial update supported).

**Auth required:** Yes

**Request body:** Any subset of profile fields (`name`, etc.)

**Response 200:** Updated profile data.

---

### POST /api/v1/songs/{id}/favorites/

Toggle a song in the authenticated user's favorites. Adds the song if not already favorited; removes it if already favorited.

**Auth required:** Yes

**Response 200:**
```json
{
  "success": true,
  "data": { "is_favorite": true }
}
```

- `is_favorite: true` — song was added to favorites
- `is_favorite: false` — song was removed from favorites

**Response 401:** Not authenticated.  
**Response 404:** Song not found.

---

### GET /api/v1/profile/favorites/

List the authenticated user's favorite songs (paginated).

**Auth required:** Yes

**Query params:**
- `?page=N` — page number (default: 1)
- `?search=<query>` — same as the songs list search: PostgreSQL full-text on name and lyrics, case-insensitive substring on author and tag names
- `?author_id=<int>` — filter to favorites by a specific author; returns 400 for non-integer values, empty list for unknown IDs
- `?tag_id=<int>` — filter to favorites with a specific tag; returns 400 for non-integer values, empty list for unknown IDs

All params are optional and combinable (AND logic).

**Response 200:**
```json
{
  "success": true,
  "data": {
    "count": 5,
    "next": null,
    "previous": null,
    "results": [{ ...song }, ...]
  }
}
```

Each song in `results` has the standard song shape (see Songs section).

**Response 401:** Not authenticated.

---

### GET /api/v1/profile/playlists/

List all playlists owned by the authenticated user (paginated).

**Auth required:** Yes

**Query params:**
- `?page=N` — page number (default: 1)

**Response 200:**
```json
{
  "success": true,
  "data": {
    "count": 3,
    "next": null,
    "previous": null,
    "results": [{ ...playlist }, ...]
  }
}
```

Each item has the standard playlist shape (see Playlists section).

**Response 401:** Not authenticated.

---

## Playlists

Playlist objects have the shape:

```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Advent Songs",
  "description": "Songs for the Advent season",
  "is_public": true,
  "is_collaborative": false,
  "owner_id": 1,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

- `is_public` — visible to all users when `true`; only the owner can access it when `false`
- `is_collaborative` — when `true`, any authenticated user can add/remove/reorder songs (not just the owner)
- Playlists are soft-deleted: `DELETE` sets `deleted_at` and hides them from all queries

---

### GET /api/v1/playlists/

List playlists (paginated).

**Auth required:** No — unauthenticated users see only public playlists; authenticated users additionally see their own private playlists.

**Query params:**
- `?page=N` — page number (default: 1)
- `?name=<query>` — case-insensitive substring match on playlist name
- `?description=<query>` — case-insensitive substring match on description

**Response 200:**
```json
{
  "success": true,
  "data": {
    "count": 10,
    "next": null,
    "previous": null,
    "results": [{ ...playlist }, ...]
  }
}
```

---

### POST /api/v1/playlists/

Create a new playlist.

**Auth required:** Yes

**Request body:**
```json
{
  "name": "Advent Songs",
  "description": "Songs for the Advent season",
  "is_public": false,
  "is_collaborative": false
}
```

- `name` — required
- `description` — optional; defaults to `""`
- `is_public` — optional; defaults to `false`
- `is_collaborative` — optional; defaults to `false`

**Response 201:**
```json
{
  "success": true,
  "data": { ...playlist }
}
```

**Response 400:** Validation error.
**Response 401:** Not authenticated.

---

### GET /api/v1/playlists/{uuid}/

Retrieve a single playlist by UUID.

**Auth required:** No for public playlists; owner required for private playlists.

**Response 200:**
```json
{
  "success": true,
  "data": { ...playlist }
}
```

**Response 403:** Playlist is private and the requesting user is not the owner.
**Response 404:** Playlist not found.

---

### POST /api/v1/playlists/{uuid}/

Partial update of a playlist. Only the fields present in the request body are changed.

**Auth required:** Yes — must be the playlist owner.

**Request body:** Any subset of `name`, `description`, `is_public`, `is_collaborative`.

**Response 200:**
```json
{
  "success": true,
  "data": { ...playlist }
}
```

**Response 400:** Validation error.
**Response 401:** Not authenticated.
**Response 403:** Not the playlist owner.
**Response 404:** Playlist not found.

---

### DELETE /api/v1/playlists/{uuid}/

Soft-delete a playlist (sets `deleted_at`; hidden from all queries).

**Auth required:** Yes — must be the playlist owner.

**Response 204:** No content.

**Response 401:** Not authenticated.
**Response 403:** Not the playlist owner.
**Response 404:** Playlist not found.

---

### GET /api/v1/playlists/{uuid}/songs/

List the songs in a playlist, ordered by their position.

**Auth required:** No for public playlists; owner required for private playlists.

**Query params:**
- `?page=N` — page number (default: 1)

**Response 200:**
```json
{
  "success": true,
  "data": {
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
      { "order": 1, "song": { ...song } },
      { "order": 2, "song": { ...song } }
    ]
  }
}
```

Each `song` has the standard song shape (see Songs section).

**Response 403:** Playlist is private and the requesting user is not the owner.
**Response 404:** Playlist not found.

---

### POST /api/v1/playlists/{uuid}/songs/attach/

Toggle songs in or out of a playlist. Songs not yet in the playlist are added; songs already in the playlist are removed. New songs are appended after the last existing position.

**Auth required:** Yes — must be the playlist owner, or any authenticated user if the playlist is collaborative.

**Request body:**
```json
{
  "song_ids": [1, 2, 3]
}
```

- `song_ids` — required; non-empty array of existing song IDs

**Response 200:**
```json
{
  "success": true,
  "data": {}
}
```

**Response 400:** Validation error or one or more song IDs not found.
**Response 401:** Not authenticated.
**Response 403:** Not the owner and playlist is not collaborative.
**Response 404:** Playlist not found.

---

### POST /api/v1/playlists/{uuid}/songs/order/

Reorder the songs in a playlist. The request must include every song currently in the playlist in the desired order.

**Auth required:** Yes — must be the playlist owner, or any authenticated user if the playlist is collaborative.

**Request body:**
```json
{
  "song_ids": [3, 1, 2]
}
```

- `song_ids` — required; must contain exactly the same song IDs currently in the playlist (no additions or removals), in the new desired order

**Response 200:**
```json
{
  "success": true,
  "data": {}
}
```

**Response 400:** Validation error or `song_ids` does not match the current set of songs in the playlist.
**Response 401:** Not authenticated.
**Response 403:** Not the owner and playlist is not collaborative.
**Response 404:** Playlist not found.

---

## Songs

Song objects have the shape:

```json
{
  "id": 1,
  "name": "Ave María",
  "views": 0,
  "tags": [{ "id": 1, "name": "Liturgia", "slug": "liturgia", "parent_id": null }],
  "authors": [{ "id": 1, "name": "Anónimo", "image": "", "bio": "", "slug": "anonimo" }],
  "plain_lyrics": "---\ntone: G\n---\n[verse]\n...",
  "tone": "G",
  "is_public": true,
  "lyrics": {
    "lyric": [...],
    "chords": [...]
  },
  "is_favorited": false
}
```

`is_favorited` — `true` if the authenticated user has favorited this song, `false` otherwise. Always `false` for unauthenticated requests.

---

### GET /api/v1/songs/

List all songs (paginated).

**Auth required:** No

**Query params:**
- `?page=N` — page number (default: 1)
- `?search=<query>` — PostgreSQL full-text search on song name and lyrics (requires full words); case-insensitive substring match on author names and tag names (partial words work)
- `?author_id=<int>` — filter to songs that have the given author; returns 400 for non-integer values, empty list for unknown IDs
- `?tag_id=<int>` — filter to songs that have the given tag; returns 400 for non-integer values, empty list for unknown IDs
- `?limit=<positive int>` — caps the number of songs returned. When present, pagination is skipped entirely and `data` is a plain array of songs instead of the paginated envelope. Returns 400 for zero, negative, or non-integer values.
- `?order_by=<views|created_at>` — field to sort by. Returns 400 for any other value.
- `?order=<asc|desc>` — sort direction, default `asc` when `order_by` (or `order` itself) is given. If `order` is given without `order_by`, it defaults `order_by` to `created_at`. If neither is given, ordering is unchanged from today: newest first (`-created_at`). Returns 400 for any value other than `asc`/`desc`.

All params are optional and combinable — each active param narrows the result set (AND logic). Example — most-viewed songs for a home page: `?limit=10&order_by=views&order=desc`.

**Response 200 (no `limit`):**
```json
{
  "success": true,
  "data": {
    "count": 120,
    "next": "http://.../api/v1/songs/?page=2",
    "previous": null,
    "results": [{ ...song }, ...]
  }
}
```

**Response 200 (with `limit`):**
```json
{
  "success": true,
  "data": [{ ...song }, ...]
}
```

---

### GET /api/v1/songs/{id}/

Retrieve a single song by ID.

**Auth required:** No

**Response 200:**
```json
{
  "success": true,
  "data": { ...song }
}
```

**Response 404:** Song not found.

---

### POST /api/v1/songs/

Create a new song.

**Auth required:** Yes — requires `can_create_songs` permission

**Request body:**
```json
{
  "name": "Song Title",
  "authors": [1, 2],
  "tags": [3],
  "lyrics": "---\ntone: G\n---\n[verse]\n..."
}
```

- `authors` — required, array of existing author IDs (at least one)
- `tags` — optional, array of existing tag IDs
- `lyrics` — must be valid song format with frontmatter (`---\ntone: <TONE>\n---`) and at least one section (`[verse]` or `[chorus]`)

**Response 201:**
```json
{
  "success": true,
  "data": { ...song }
}
```

**Response 400:** Validation error (invalid lyrics format, unknown author IDs).  
**Response 401:** Not authenticated.  
**Response 403:** Missing `can_create_songs` permission.

---

### PUT /api/v1/songs/{id}/

Full update of a song. Replaces all mutable fields; omitting `tags` clears the tag list.

**Auth required:** Yes — requires `can_create_songs` permission

**Request body:**
```json
{
  "name": "Song Title",
  "authors": [1, 2],
  "tags": [3],
  "lyrics": "---\ntone: G\n---\n[verse]\n..."
}
```

- `authors` — required, array of existing author IDs (at least one)
- `tags` — optional; defaults to `[]` if omitted, which clears all tags
- `lyrics` — must be valid song format; `tone` is re-derived from the frontmatter

**Response 200:** Updated song object.

**Response 400:** Validation error (invalid lyrics, unknown IDs).  
**Response 401:** Not authenticated.  
**Response 403:** Missing `can_create_songs` permission.  
**Response 404:** Song not found.

---

### PATCH /api/v1/songs/{id}/

Partial update of a song. Only the fields present in the request body are changed.

**Auth required:** Yes — requires `can_create_songs` permission

**Request body:** Any subset of `name`, `authors`, `tags`, `lyrics`.

- `authors` — if provided, replaces the current author list (at least one required)
- `tags` — if provided, replaces the current tag list (`[]` clears all tags); omitting the key leaves tags unchanged
- `lyrics` — if provided, `tone` is re-derived from the updated frontmatter

**Response 200:** Updated song object.

**Response 400 / 401 / 403 / 404:** Same as PUT.

---

### DELETE /api/v1/songs/{id}/

Delete a song.

**Auth required:** Yes — requires `can_create_songs` permission

**Response 204:** No content.

**Response 401:** Not authenticated.  
**Response 403:** Missing `can_create_songs` permission.  
**Response 404:** Song not found.

---

### POST /api/v1/songs/{id}/publish/

Publish a song (sets `is_public = true`).

**Auth required:** Yes — requires `can_publish_songs` permission

**Response 200:**
```json
{
  "success": true,
  "data": { ...song }
}
```

**Response 401 / 403:** Auth or permission errors.

---

### POST /api/v1/songs/{id}/transport/

Transpose the song's chords to a different tone.

**Auth required:** No

**Request body:**
```json
{
  "transport": "semi_tone" | "tone",
  "current_tone": "G",
  "original_tone": "G"
}
```

**Response 200:** Song object with `lyrics` transposed to the new tone.

**Response 400:** Invalid tone value.

---

### POST /api/v1/songs/{id}/view/

Register a view on a song. Increments the song's `views` counter by one (atomic — safe under concurrent requests) and returns the updated song.

**Auth required:** No

**Response 200:**
```json
{
  "success": true,
  "data": { ...song }
}
```

**Response 404:** Song not found.

---

## Authors

Author objects have the shape:

```json
{
  "id": 1,
  "name": "San Juan de la Cruz",
  "image": "https://example.com/sjdc.jpg",
  "bio": "Místico y poeta español del siglo XVI.",
  "slug": "san-juan-de-la-cruz"
}
```

---

### GET /api/v1/authors/

List all authors (paginated).

**Auth required:** No

**Query params:**
- `?page=N`
- `?search=<query>` — full-text search on author name and bio

**Response 200:**
```json
{
  "success": true,
  "data": {
    "count": 45,
    "next": null,
    "previous": null,
    "results": [{ ...author }, ...]
  }
}
```

---

### GET /api/v1/authors/{id}/

Retrieve a single author.

**Auth required:** No

**Response 200:**
```json
{
  "success": true,
  "data": { ...author }
}
```

**Response 404:** Author not found.

---

### POST /api/v1/authors/

Create an author.

**Auth required:** Yes — `can_create_songs`

**Request body:**
```json
{
  "name": "Sor Suzanne",
  "image": "https://example.com/img.jpg",
  "bio": "Compositora religiosa.",
  "slug": "sor-suzanne"
}
```

- `name` — required
- `slug` — optional; auto-generated from name if omitted

**Response 201:**
```json
{
  "success": true,
  "data": { ...author }
}
```

---

### PUT /api/v1/authors/{id}/

Full update of an author.

**Auth required:** Yes — `can_create_songs`

**Request body:** Same as POST. `slug` is re-generated from name if omitted.

**Response 200:** Updated author.

---

### PATCH /api/v1/authors/{id}/

Partial update of an author.

**Auth required:** Yes — `can_create_songs`

**Request body:** Any subset of author fields.

**Response 200:** Updated author.

---

### DELETE /api/v1/authors/{id}/

Delete an author.

**Auth required:** Yes — `can_create_songs`

**Response 204:** No content.

---

### GET /api/v1/authors/{id}/songs/

List songs by a specific author (paginated).

**Auth required:** No

**Query params:** `?page=N`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "count": 12,
    "next": null,
    "previous": null,
    "results": [{ ...song }, ...]
  }
}
```

**Response 404:** Author not found.

---

## Tags

Tag objects have the shape:

```json
{
  "id": 1,
  "name": "Adviento",
  "slug": "adviento",
  "parent_id": null
}
```

Tags can be nested — `parent_id` references another tag's `id`.

---

### GET /api/v1/tags/

List all tags (paginated).

**Auth required:** No

**Query params:**
- `?page=N`
- `?search=<query>` — full-text search on tag name

**Response 200:**
```json
{
  "success": true,
  "data": {
    "count": 30,
    "next": null,
    "previous": null,
    "results": [{ ...tag }, ...]
  }
}
```

---

### GET /api/v1/tags/{id}/

Retrieve a single tag.

**Auth required:** No

**Response 200:**
```json
{
  "success": true,
  "data": { ...tag }
}
```

**Response 404:** Tag not found.

---

### POST /api/v1/tags/

Create a tag.

**Auth required:** Yes — `can_create_songs`

**Request body:**
```json
{
  "name": "Semana Santa",
  "slug": "semana-santa",
  "parent_id": null
}
```

- `name` — required
- `slug` — optional; auto-generated if omitted; must be unique
- `parent_id` — optional; ID of parent tag

**Response 201:**
```json
{
  "success": true,
  "data": { ...tag }
}
```

**Response 400:** Duplicate slug or invalid parent ID.

---

### PUT /api/v1/tags/{id}/

Full update of a tag.

**Auth required:** Yes — `can_create_songs`

**Response 200:** Updated tag.

---

### PATCH /api/v1/tags/{id}/

Partial update of a tag.

**Auth required:** Yes — `can_create_songs`

**Response 200:** Updated tag.

---

### DELETE /api/v1/tags/{id}/

Delete a tag.

**Auth required:** Yes — `can_create_songs`

**Response 204:** No content.

---

### GET /api/v1/tags/{id}/songs/

List songs with a specific tag (paginated).

**Auth required:** No

**Query params:** `?page=N`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "count": 8,
    "next": null,
    "previous": null,
    "results": [{ ...song }, ...]
  }
}
```

**Response 404:** Tag not found.

---

### GET /api/v1/tags/{id}/children/

List direct child tags.

**Auth required:** No

**Response 200:**
```json
{
  "success": true,
  "data": [{ ...tag }, ...]
}
```

**Response 404:** Tag not found.

---

## Error Responses

All errors follow this shape:

```json
{
  "success": false,
  "data": {},
  "errors": ["Error message" | { "field": ["error detail"] }],
  "message": ""
}
```

| Status | Meaning |
|--------|---------|
| 400 | Validation error — check `errors` for field details |
| 401 | Authentication required — include `Authorization: Bearer <token>` |
| 403 | Permission denied — user lacks required permission |
| 404 | Resource not found |
| 415 | Content-Type must be `application/json` for POST/PUT/PATCH |
| 429 | Rate limit exceeded — auth endpoints: 10/min; general: 1000/hour authenticated, 100/hour anonymous |
