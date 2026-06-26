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

---

## Source Database Format (Legacy Laravel Import Reference)

The old Laravel app stored lyrics in two places on the `songs` table. The importer in `cc/songs/importer.py` reads from both, preferring the `verses` table when it exists.

### `lyrics` column (JSON array)

Each song's lyrics were stored as a JSON array of sections:

```json
[
  {"type": "verse", "data": {"content": "<p>Lyric line one&nbsp;</p><p>Lyric line two</p>"}},
  {"type": "chorus", "data": {"content": "<p>Chorus line</p>"}}
]
```

Key characteristics of the HTML content:
- Each lyric line is wrapped in a `<p>...</p>` tag (output of the WYSIWYG editor).
- Lines often end with `&nbsp;` (trailing non-breaking space inserted by the editor).
- `<br>` tags also appear for inline line breaks within a paragraph.
- Content may contain `\r\n` (Windows-style line endings) from some browser/OS combinations.
- Valid `type` values: `"verse"`, `"chorus"`, `"bridge"`. Any other type is imported as `verse`.

The importer's `_strip_html` function handles all of these: it converts `</p>` and `<br>` to `\n`, cleans `&nbsp;`, normalizes `\r\n` to `\n`, and strips trailing spaces from each line. Empty sections are skipped. Multiple consecutive blank lines within a section are collapsed to a single newline.

### `verses` table (preferred when present)

When the dump contains a `verses` table, the importer uses it instead of the `lyrics` JSON column. Each row is a section:

| column | description |
|--------|-------------|
| `song_id` | FK to songs |
| `order` | display order (ascending) |
| `verse_type` | `1`=verse, `2`=chorus, `3`=bridge, `4`/`5`=verse |
| `content` | plain text with inline chord notation |

Inline chords use square brackets: `Porque[C] eres la razón[G]`. The importer converts these to the positional `{C}` format on a chord line above the lyric line.

### `lyrics_with_chords` column

Plain-text chord sheet (not HTML). The importer does **not** use this column — the `verses` table supersedes it when present, and the `lyrics` JSON column is used otherwise.
