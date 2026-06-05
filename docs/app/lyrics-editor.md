# Lyrics Editor

To create a lyric for a song, we use a format similar in markdown. The goal is to accept a format that let us parse it and give a format correctly in depends of needs (if wants only lyrics and if wants lyrics + chords)

## Lyrics Editor Syntax

We should follow the following syntax:

## Heading

Is required that a lyric content contains at the top the following information wrapper by this: "---" like:

```text
---
tone: G
guitar_capo: false
---
```

We should accept only these keywords:

- "tone": it must be required and the backend should validate that value is a valid music tune. Otherwise, it will return an error: "Lyric Tone is invalid. Please use a valid tone."
- "guitar_capo": it should not be required and the value must be only "true" or "false".

Is required that these values are always at the beggining of the lyrics content. If the content does not exists, we should also return an error. Please be sure to create a config.

## Lyric content.

We should structure or split the lyric content for a better visualization. For this, we need to use the following keywords:

- "verse": Should not be required. it should be in lowercase.
- "chorus": Should not be required. It should be in lowercase.
- "bridge": Should not be required. It should be in lowercase.

Every keyword will be wrapped in brakets and it will work as a delimiter.

Example:

```text
[verse]
Porque eres la razón de mi vida
Mi fuerza consuelo y alegría
Porque eres el amor que yo soñé
Y sin Ti estoy perdido y nada soy

[chorus]
Aquí estoy Señor toma mi vida
Sacerdote para siempre quier ser
```

This will be equal to:

```txt
Porque eres la razón de mi vida
Mi fuerza consuelo y alegría
Porque eres el amor que yo soñé
Y sin Ti estoy perdido y nada soy

Aquí estoy Señor toma mi vida
Sacerdote para siempre quier ser
```

## Lyric Chords

Now, we need to add chords to the song. And chords needs to be well localized, also, we need to have the ability to change tone if needed. So, for this
we'll use the following pattern: "{G} or {A,B}"

For instance:

```
[verse]
     {G}                   {D}
Porque eres la razón de mi vida
 {C}      {D}        {G}
Mi fuerza consuelo y alegría
       {C}                    {G}
Porque eres el amor que yo soñé
      {Em}                    {D}
Y sin Ti estoy perdido y nada soy

[chorus]
        {G}                {D}
Aquí estoy Señor toma mi vida
      {D}        {D}              {G}
Sacerdote para siempre quiero ser
                          {D}
Aquí estoy Señor toma mi  vida
      {C}        {D}           {Em,A,C,D}
Sacerdote para siempre quiero ser
```

So, this will be translated to:

```
      G                    D
Porque eres la razón de mi vida
  C       D          G
Mi fuerza consuelo y alegría
       C                      G
Porque eres el amor que yo soñé
       Em                     D
Y sin Ti estoy perdido y nada soy

        G                D
Aquí estoy Señor toma mi vida
      D        D              G
Sacerdote para siempre quiero ser
                          D
Aquí estoy Señor toma mi  vida
      C        D              Em  A C D
Sacerdote para siempre quiero ser
```

## The API response

What we just discussed is the way how the songs will be written. However, we use another format for the API response. On the API response we need to send an array, like this:

For this song lyric:

```
---
tone: G
---
[verse]
     {G}                   {D}
Porque eres la razón de mi vida
 {C}      {D}        {G}
Mi fuerza consuelo y alegría
       {C}                    {G}
Porque eres el amor que yo soñé
      {Em}                    {D}
Y sin Ti estoy perdido y nada soy

[chorus]
        {G}                {D}
Aquí estoy Señor toma mi vida
      {D}        {D}              {G}
Sacerdote para siempre quiero ser
                          {D}
Aquí estoy Señor toma mi  vida
      {C}        {D}           {Em,A,C,D}
Sacerdote para siempre quiero ser
```

We should return in the song payload the following:

```
{
    "id": 1,
    "name": "Sacerdote para siempre",
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
    "plain_lyrics": " // we return here the saved content.
        ---
        tone: G
        ---
        [verse]
            {G}                   {D}
        Porque eres la razón de mi vida
        {C}      {D}        {G}
        Mi fuerza consuelo y alegría
            {C}                    {G}
        Porque eres el amor que yo soñé
            {Em}                    {D}
        Y sin Ti estoy perdido y nada soy

        [chorus]
                {G}                {D}
        Aquí estoy Señor toma mi vida
            {D}        {D}              {G}
        Sacerdote para siempre quiero ser
                                {D}
        Aquí estoy Señor toma mi  vida
            {C}        {D}           {Em,A,C,D}
        Sacerdote para siempre quiero ser
    ",
    "tone": "G", // we take this from the lyric content
    "is_public": true,
    "lyrics": {
        "lyric": [ // this is the song without chords
            {
                "type": "verse",
                "content": "
                    Porque eres la razón de mi vida
                    Mi fuerza consuelo y alegría
                    Porque eres el amor que yo soñé
                    Y sin Ti estoy perdido y nada soy
                "
            },
            {
                "type": "chorus",
                "content": "
                    Aquí estoy Señor toma mi vida
                    Sacerdote para siempre quiero ser
                    Aquí estoy Señor toma mi vida
                    Sacerdote para siempre quiero ser
                "
            }
        ],
        "chords": [
            {
                "type": "verse",
                "content": "
                          G                    D
                    Porque eres la razón de mi vida
                    C       D          G
                    Mi fuerza consuelo y alegría
                        C                      G
                    Porque eres el amor que yo soñé
                        Em                     D
                    Y sin Ti estoy perdido y nada soy
                "
            },
            {
                "type": "chorus",
                "content": "
                            G                D
                    Aquí estoy Señor toma mi vida
                        D        D              G
                    Sacerdote para siempre quiero ser
                                            D
                    Aquí estoy Señor toma mi  vida
                        C        D              Em  A C D
                    Sacerdote para siempre quiero ser
                "
            }
        ]
    }
}
```

## Chord Transport

We have the functionality to transport songs.
So, we need to create an algorithm that takes the chords defined in the editor and transport it by mid tones.
