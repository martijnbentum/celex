# celex

Parser for the CELEX-2 lexical database (Dutch, English, German).

Parses the phonology files (`DPW.CD`, `EPW.CD`, `GPW.CD`) into `Word`,
`Syllable` and `Phone` objects with DISC, CELEX and IPA transcriptions,
stress, syllable structure (onset, nucleus, coda, rhyme) and
ambisyllabicity. IPA symbols come from
[phone_mapper](https://github.com/martijnbentum/phone_mapper).

## Installation

```bash
uv venv .venv --python 3.12
uv sync
```

## Usage

```python
import celex

words = celex.load('dutch')          # also: 'english', 'german'
word = words[4]

word.word                # 'aagtappel'
word.ipa                 # 'aː x t ɑ p ə l'
word.stress_pattern      # 's w w'   (s strong, w weak, ss secondary)
word.multiword           # False
word.frequency           # corpus frequency (inl/cob/mann column)

syllable = word.syllables[0]
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

phone = word.phones[4]
phone.disc               # 'p'
phone.celex              # 'p'
phone.ipa                # 'p'
phone.phoneme_type       # 'consonant' | 'vowel' | 'syllabic_consonant'
phone.cv                 # 'C' | 'V' | 'VV' | 'S'
phone.ambisyllabic       # True (written [A[p]@l] in the source)
phone.prev, phone.next   # neighbouring phones in the word
phone.syllable, phone.word
phone.surface_syllables  # two syllables when ambisyllabic, else one
```

English entries can have multiple pronunciations; the first one is the
returned `Word` and the others are `Word` objects in
`word.pronunciations`.

Entries without a parsable pronunciation are skipped: 2938 Dutch
entries have no pronunciation and 3 entries (1 German typo, 1 corrupt
German entry, 1 inconsistent English entry) have columns that do not
align.
