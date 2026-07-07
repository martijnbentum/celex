# CELEX Data Structure

## Location

The full CELEX dataset lives in `CELEX_DATA/` (gitignored — licensed data).
It is organised by language (`DUTCH/`, `ENGLISH/`, `GERMAN/`) and then by
file type.

## data/ directory

`data/` is also gitignored (licensed data). It contains:

- `DPW.CD`, `EPW.CD`, `GPW.CD` — older copies of the phonology word-form
  files, superseded by `CELEX_DATA/*/DPW/` etc.
- `dutch_header`, `english_header`, `german_header` — hand-crafted column
  name files used by the parser to map DPW fields by name. These are the
  only files in `data/` that are still actively used; the `.CD` files there
  are no longer read.
- `OLD/EPL/` — an older copy of the English phonology lemma file.

## CELEX_DATA/DUTCH/ folders

Each folder name follows the pattern `D<domain><scope>`:

| Folder | Full name | Contents |
|--------|-----------|----------|
| **DAB** | Dutch **A**b**b**reviations | Abbreviations with frequency and spelling variants |
| **DCT** | Dutch **C**orpus **T**ypes | Raw corpus word types with frequency and dispersion |
| **DFL** | Dutch **F**requency, **L**emmas | Lemma-level frequency: raw count, per-million, log, dictionary flag |
| **DFW** | Dutch **F**requency, **W**ord forms | Word-form frequency linked to lemma |
| **DFS** | Dutch **F**requency, **S**yllables | Phonetic syllable frequencies (not in original User Guide — a later addition) |
| **DML** | Dutch **M**orphology, **L**emmas | Morphological structure: derivation/compounding, constituent structure labels |
| **DMW** | Dutch **M**orphology, **W**ord forms | Inflectional features of word forms (inflection type, separability) |
| **DOL** | Dutch **O**rthography, **L**emmas | Headword spellings, syllabification, stem forms, spelling variants |
| **DOW** | Dutch **O**rthography, **W**ord forms | Word-form spellings, syllabification, spelling variants |
| **DPL** | Dutch **P**honology, **L**emmas | Phonological transcription of lemma headwords (primary + secondary pronunciation). **`IdNumLemma` in DPW references IDs in this file.** |
| **DPW** | Dutch **P**honology, **W**ord forms | Phonological transcription of all inflected/derived word forms — the main file loaded by the parser |
| **DSL** | Dutch **S**yntax, **L**emmas | Syntactic properties: word class, gender, definiteness, auxiliary type, subcategorisation |

The same pattern applies to `ENGLISH/` (prefix `E`) and `GERMAN/` (prefix `G`),
with minor structural differences (e.g. English EPL allows more than two
pronunciation variants per entry; German GPL has a different field order for
cv and celex columns).

## ID namespaces

There are two separate ID spaces within each language:

- **Lemma IDs** — shared across DPL, DML, DOL, DFL, DSL (all `*L` files)
- **Word-form IDs** — shared across DPW, DMW, DOW, DFW (all `*W` files)

The `IdNumLemma` field in any `*W` file references the **lemma ID space**,
not the word-form ID space. Matching `IdNumLemma` against `IdNum` within
the same `*W` file will produce incorrect results (coincidental id collisions
from a different namespace).
