# Routes

This is a mapping of routes in general to have a clear reference of existing endpoints and future endpoints.

This is the format:

```
{HTTP_METHOD} - {PATH} - {VISIBILITY (public or private)}
Payload: {PAYLOAD (if needed)}
Response: {OBJECT RESPONSE}
```

The response structure will always be:

```
{
    "data": {...},
    "errors": [],
    "message": "",
    "success": true or false
}
```

## Authentication

For register and login, we use the Email Token logic. What is the email token logic?
We send a unique and expirable token to the user in 6 digits format: "ABC123".

So, when the user register, the account is set "is_active = false"
and the user recieves the email token with an expiration of 20mins.
User should be able to enter that token and login automatically. (The user changes "is_active = true")

### Register

When register we validate that:

1. We should lowercase the email
2. We should ensure that there is not an user with the provided email.
3. If there is a customer with the email alreday, we should ask customer to login instead.

```
POST - /api/auth/register - public
Payload: {
    "name": "David Gaitan",
    "email": "mail@mail.com",
    "password": "password"
}
Response: {
    "data": {},
    "message": "Check you email inbox and use the code to login"
    // ...
}
```

### Verify Email Token

The backend should validate if the token matches the email and if token is not expired.

```
POST - /api/auth/verify - public
Payload: {
    "email": "mail@mail.com",
    "token": "ABC123"
}
Response: {
    "data": {
        "access_token": "...",
        "refresh_token": "..."
    },
    "message": "Email successfuly verified"
}
```

### Login

User should login using email and password, and then, it should fires a new email with a token to validate authenticity.

```
POST - /api/auth/login - public
Payload: {
    "email": "mail@mail.com",
    "password": "password"
}
Response: {
    "data": {},
    "message": "Check you email inbox and use the code to login"
    // ...
}
```

### Refresh Token

This is in case that access token is expired (access token should expires daily)

```
POST - /api/auth/refres-token - private
Payload: {
    "refresh_token": "..."
}
Response: {
    "data": {
        "access_token": "...",
        "refresh_token": "..."
    },
    ...
}
```

### Logout

This is an endpooint to logout session (expire token).

```
POST - /api/auth/logout
Payload: {
    "access_token": "...",
    "email": "mail@amil.com"
}
Response {
    "data": {}
    "message": "Successfully Logged out"
}
```

## Users

### Profile

```
GET - /api/v1/profile - private
Payload: {}
Response: {
    "data": {
        "id": 1,
        "email": "mail@mail.com",
        "name": "David Gaitan",
        "can_create_songs": true,
        "can_publish_songs": true,
        "can_create_playlists": true
    }
}
```

### Update Profile

For now, only name can be updated. Email is not possible to update.

```
PUT - /api/v1/profile - private
Payload: {
    "name": "David Gaitan"
}
Response: {
     "data": {
        "id": 1,
        "email": "mail@mail.com",
        "name": "David Gaitan",
        "can_create_songs": true,
        "can_publish_songs": true,
        "can_create_playlists": true
    }
    ...
}
```

## Songs

This is the song Payload:

```
{
    "id": 1,
    "name": "Yo soy el Pand de Vida",
    "views": 10,
    "tags": [
        {
            "id": 1,
            "name": "Misa"
        },
        {
            "id": 2,
            "name": "Adoración"
        }
    ],
    "authors": [
        {
            "id": 1,
            "name": "Sor Sussane"
        },
    ],
    "plain_lyrics": "...",
    "tone": "G",
    "is_public": true,
    "lyrics": {
        "lyric": [
            {
                "type": "verse",
                "content": "..."
            },
            {
                "type": "chorus",
                "content": "..."
            }
            ...
        ],
        "chords": [
            {
                "type": "verse",
                "content": "..."
            },
            {
                "type": "chorus",
                "content": "..."
            }
        ]
    }
}
```

Songs is the main directory.

### Get a song

```
GET - /api/v1/songs/{id} - public
Payload: {}
Response: {
    "data" : { ... Song Payload ... }
}
```

### Create a Song

For perform a request to this is needed that user have "user.can_create_songs" to true. The Song will always ruturn "is_public = false". Which
means that only those songs with "is_public = true" will be available for the world publicly. It will required another action to publish it.

```
POST - /api/v1/songs - private
Payload: {
    "name": "Song Name",
    "authors": [authors ids],
    "tags": [tag ids],
    "lyrics": "..." // we will talk about this
}
Response {
    "data" {...SongPayload...}
    ...
}
```

### Publish a Song

An user that have "user.can_create_songs = true", cannot public a song. So, this action is to publish it. And only those users that have "user.can"

```
POST - /api/v1/songs/{id}/publish - private
Payload: {}
Response: {
    "data": "...Song Payload...",
    ...
}
```

### Transport Song Chords

This is used to transport a song from a chord to another one.

```
POST - /api/v1/songs/{id}/transport - public
Payload: {
    "transport": "semi_tone" // it can be "tone" or "semi_tone".
    "current_tone": "F" // the current tone (this is not the original tone stored, is the current one after the latest transport)
    "original_tone": "G" // original tone.
}
Response: {
    "data": "...Song Payload with the chords transported...",
    ....
}
```
