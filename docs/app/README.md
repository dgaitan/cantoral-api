# Cantoral App

Cantoral is the official Catholic Cantoral where we provide lyrics for catholic songs, but also we provide lyrics with chords. This is a database of songs where we provide the entire lyrics with chord management. This is a powerful tool also to generate song sets for mass and special events using the power of AI.

## Django Apps.

### Songs

The song app is the main directory. We use this app to store the authors, songs, albums, videos and folders.

### Playlists

The playlists is functionality to have playlists using the songs collection. These are created by users.

### Users

Main user reference. We have the users here. We have a single type users but with permissions. We have permissions like:

- can_contribute (create or update songs)
- can_publish (can publis a song, author or any other content publicly)
- can_create_playlist (if the user can create songs)

## Features

I am listing here the features from high to lower priority:

### Users

We need to have the ability to create accounts and start using the app. We want to have the auth endpoints under these endpoints:

### Song Creation

This app is mainly focused on store lyrics, but also is important crucial to have chords. We need to have a powerful content editor for lyrics that are used. You can find more information about the lyrics editor here: [lyrics editor](./lyrics-editor.md)

### Algolia Integration.

For a better search experience, we use Algolia. So, we will have a connection with algolia that:

- When a song is set to "is_public = true" we should sync it with algolia.
- When we update a song and the song is still "is_public = true" we should sync with algolia.
- We should validate always that if song value changes from "is_public = true" to "is_public = false", we should remove it from Algolia.
