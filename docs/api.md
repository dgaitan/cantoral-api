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

**Search:** All list endpoints accept `?search=<query>` for PostgreSQL full-text search. Search uses word-level tokenization — type full words for best results.

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
  }
}
```

---

### GET /api/v1/songs/

List all songs (paginated).

**Auth required:** No

**Query params:**
- `?page=N` — page number (default: 1)
- `?search=<query>` — full-text search across song name, lyrics, author names, and tag names

**Response 200:**
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
