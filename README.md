# celex

Parser for the CELEX-2 lexical database (Dutch, English, German).

Parses the phonology files (`DPW.CD`, `EPW.CD`, `GPW.CD`) into `Word`,
`Syllable` and `Phone` objects with DISC, CELEX and IPA transcriptions,
stress, syllable structure (onset, nucleus, coda, rhyme) and
ambisyllabicity. IPA symbols come from
[phone_mapper](https://github.com/martijnbentum/phone_mapper).

## CELEX data

This package requires the CELEX-2 CD-ROM data (licensed, not included).
Place the unzipped disc contents at `CELEX_DATA/` in the repository root
or set the `CELEX_DATA` environment variable to that directory:

```bash
export CELEX_DATA=/path/to/CELEX_DATA
```

The directory structure should look like:

```
CELEX_DATA/
  DUTCH/
    DPW/DPW.CD      ← phonology word forms (loaded by Lexicon/load)
    DPL/DPL.CD      ← phonology lemmas    (loaded for word.lemma)
    ...
  ENGLISH/
    EPW/EPW.CD
    EPL/EPL.CD
    ...
  GERMAN/
    GPW/GPW.CD
    GPL/GPL.CD
    ...
```

`CELEX_DATA/` is gitignored. See `NOTES/celex_data_structure.md` for a
description of all subfolders.

## Parse cache

Parsing a full language file takes ~14 seconds, so `load()`,
`load_lemmas()` and `Lexicon` cache their results as pickles in
`~/.cache/celex`, keyed on the data file's modification time and
size. A cached load is roughly 2-3x faster. Expect ~270 MB per
language; each language uses one fixed cache file that is
overwritten when the data or parser changes, so the cache never
grows beyond one file per language.

Set the `CELEX_CACHE` environment variable to relocate the cache, or
pass `use_cache=False` to skip it:

```python
words = celex.load('dutch', use_cache=False)
lexicon = celex.Lexicon('dutch', use_cache=False)
```

## Installation

### Install with `pip`

```bash
pip install git+https://github.com/martijnbentum/celex.git
```

### Install with `uv pip`

```bash
uv pip install git+https://github.com/martijnbentum/celex.git
```

### Development setup

```bash
uv venv .venv --python 3.12
uv sync
```

## Usage

### Lexicon

```python
from celex import Lexicon

lex = Lexicon('dutch')           # also: 'english', 'german'
lex.words                        # list of Word objects in file order

# query roots - exact matching by default, substring with __contains
lex.query.words.filter(label='lopen')                 # exact label match
lex.query.words.filter(label__contains='op')          # substring label match
lex.query.words.filter(ipa__contains='aː x')          # IPA substring
lex.query.words.filter(stress_pattern='s w')
lex.query.words.filter(frequency__gte=100)

lex.query.syllables.filter(label__contains='aː')
lex.query.syllables.filter(stress='strong')           # 'strong' | 'weak' | 'secondary'

lex.query.phones.filter(label='p')                    # exact IPA symbol
lex.query.phones.filter(position='onset')             # 'onset' | 'nucleus' | 'coda'
lex.query.phones.filter(ambisyllabic=True)
lex.query.phones.filter(stressed=True)                # phone in a stressed syllable

# word navigation and lemma links
word = lex.query.words.get(label='loopt')
word.prev, word.next             # neighbours in file order
word.lemma                       # Word from the phonology lemma file (DPL/EPL/GPL)
word.siblings                    # other DPW words sharing the same lemma id
word.family                      # [lemma, word, *siblings]
```

### Low-level access

```python
import celex

words = celex.load('dutch')          # also: 'english', 'german'
word = words[4]

word.word                # 'aagtappel'
word.label               # 'aagtappel'
word.key                 # 'dutch:word:7:p0'
word.ipa                 # 'aː x t ɑ p ə l'
word.stress_pattern      # 's w w'   (s strong, w weak, ss secondary)
word.multiword           # False
word.frequency           # corpus frequency (inl/cob/mann column)
word.parent              # None
word.children            # word.syllables

syllable = word.syllables[0]
syllable.label           # 'aː x t'
syllable.key             # 'dutch:word:7:p0:syllable:0'
syllable.ipa             # 'aː x t'
syllable.stress          # 'strong' | 'weak' | 'secondary'
syllable.onset           # phones before the nucleus
syllable.nucleus         # vowel or syllabic consonant phones
syllable.coda            # phones after the nucleus
syllable.rhyme           # nucleus + coda
syllable.weight          # 'light' | 'heavy' | 'superheavy'
                         # rhyme cv slots: 1, 2, 3+; onset is weightless
syllable.surface_phones  # phones plus a shared ambisyllabic phone
syllable.surface_rhyme   # rhyme closed by shared ambisyllabic phones
syllable.surface_weight  # weight over the surface rhyme
syllable.prev, syllable.next
syllable.parent          # word
syllable.children        # syllable.phones

phone = word.phones[4]
phone.label              # 'p'
phone.key                # 'dutch:word:7:p0:phone:4'
phone.disc               # 'p'
phone.celex              # 'p'
phone.ipa                # 'p'
phone.phoneme_type       # 'consonant' | 'vowel' | 'syllabic_consonant'
phone.cv                 # 'C' | 'V' | 'VV' | 'S'
phone.ambisyllabic       # True (written [A[p]@l] in the source)
phone.prev, phone.next   # neighbouring phones in the word
phone.syllable, phone.word
phone.surface_syllables  # two syllables when ambisyllabic, else one
phone.parent             # phone.syllable
phone.children           # []
```

The cv timing tier is a parallel structure built lazily from the
phones; the tree holds no references back to it:

```python
tier = word.timing
tier.pattern             # 'VVCCVCVC'
tier.slots[0].kind       # 'V'
tier.slots[0].phone      # long vowels link one phone to two slots
tier.slots[4].syllables  # ambisyllabic: one slot, two syllables
tier.phone_to_slots(word.phones[0])
tier.syllable_to_slots(word.syllables[1])          # own slots
tier.surface_syllable_to_slots(word.syllables[1])  # plus shared slot
```

### Syllabifier training data

`training_examples` yields the phones of each word with per position
syllable boundary labels, for training a syllabifier on CELEX
boundaries (e.g. in
[dutch_syllabifier](https://github.com/martijnbentum/dutch-syllabifier)):

```python
from celex import training_examples, word_to_example

for phones, labels, word in training_examples('dutch'):
    phones               # ['aː', 'x', 'j', 'ə']
    labels               # [0, 1, 0]  (1: boundary after this phone)
    word                 # the Word object (lemma id, frequency, ...)

word_to_example(word)    # (phones, labels) for a single Word
```

Multiword entries are skipped unless `multiword=True`. Ambisyllabic
phones follow the disc column split: they count in the syllable that
stores them.

English entries can have multiple pronunciations; the first one is the
returned `Word` and the others are `Word` objects in
`word.pronunciations`.

Entries without a parsable pronunciation are skipped: 2938 Dutch
entries have no pronunciation and 3 entries (1 German typo, 1 corrupt
German entry, 1 inconsistent English entry) have columns that do not
align.
