# English alternate pronunciations are not indexed

Review finding from 2026-07-08.

English word-form rows can contain multiple pronunciation groups. The parser
keeps the first pronunciation as the returned `Word` and stores the rest in
`word.pronunciations`, but `Lexicon` only links and queries `self.words`.

Impact:

- Alternate English pronunciations are absent from `lexicon.query.words`.
- Their syllables and phones are absent from `lexicon.query.syllables` and
  `lexicon.query.phones`.
- Variant `Word` objects are not assigned `lexicon`, `index`, `lemma`, or
  siblings.

Observed with bundled data:

- English primary words: 160,595
- Alternate pronunciations attached under primary words: 96,228
- Alternate-pronunciation syllables not exposed by lexicon flat views: 325,457
- Alternate-pronunciation phones not exposed by lexicon flat views: 834,603

Fixture reproduction:

```python
from celex import Lexicon
from celex.parser import languages, parse_line
from tests.test_celex import rhythm

header = languages["english"].read_text().split()
word = parse_line(rhythm, header, "english")
lexicon = Lexicon._from_words([word])

assert word.pronunciations[0].ipa == "r ɪ ð m̩"
assert list(lexicon.query.words.filter(ipa__contains="m̩")) == []
assert word.pronunciations[0].lexicon is None
```

Likely fix direction:

Add an explicit flattened pronunciation view on `Lexicon`, for example
`Lexicon.pronunciations` or `Lexicon.word_forms`, that includes each primary
word and its alternate pronunciations. Then decide which search APIs should
search primary entries only versus all pronunciations. If the query roots are
intended to support pronunciation search, they should use the flattened view
and tests should cover English alternates.
