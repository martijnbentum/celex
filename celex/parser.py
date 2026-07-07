'''Parse the CELEX phonology files into Word objects.

The disc column is the source of truth: one character per phone,
- or space between syllables, leading ' or " for stress. The celex
column uses language specific notation (e.g. English O is a different
vowel than Dutch O), so its ipa value is not trusted; the column is
tokenized under two constraints: one token per disc phone and the
token class (vowel, consonant, syllabic consonant) must match the
disc phone. Nested brackets in the celex column, e.g. [A[p]@l], mark
ambisyllabic phones. The cv column is checked against the cv slots
derived from the phones.
'''

import re

from phone_mapper import celex_to_ipa, disc_to_ipa

from . import locations
from .models import Phone, Syllable, Word, phoneme_type


class ParseError(ValueError):
    '''Raised when a pronunciation cannot be parsed.'''


languages = {
    'dutch': (locations.dutch, locations.dutch_header),
    'english': (locations.english, locations.english_header),
    'german': (locations.german, locations.german_header)}

def _celex_token_types():
    types = {}
    for token, ipa in celex_to_ipa.items():
        types[token] = phoneme_type(ipa)
    return types


celex_token_types = _celex_token_types()
max_token_length = max(len(token) for token in celex_token_types)


def load(language, verbose=True):
    '''Parse the phonology file of a language into Word objects.
    language:    dutch, english or german
    verbose:     print a summary of skipped entries
    '''
    if language not in languages:
        m = f'unknown language {language!r}, '
        m += "expected 'dutch', 'english' or 'german'"
        raise ValueError(m)
    path, header_path = languages[language]
    header = header_path.read_text().split()
    words, skipped = [], 0
    with open(path, encoding='latin-1') as fin:
        for line in fin:
            word = parse_line(line.rstrip('\n'), header, language)
            if word is None: skipped += 1
            else: words.append(word)
    if verbose and skipped:
        print(f'skipped {skipped} {language} entries without a '
            'parsable pronunciation')
    return words


def parse_line(line, header, language):
    '''Parse one data file line into a Word, or None on failure.'''
    parts = line.split('\\')
    if language == 'english': return _parse_english_line(parts, header)
    fields = dict(zip(header, parts))
    try:
        syllables = parse_pronunciation(fields['disc'], fields['cv'],
            fields['celex'])
    except ParseError:
        return None
    return _make_word(fields, header, syllables, language)


def parse_pronunciation(disc, cv, celex):
    '''Build Syllable objects from the three pronunciation columns.
    Raises ParseError if the columns cannot be aligned.'''
    if not disc: raise ParseError('empty pronunciation')
    syllables = _disc_syllables(disc)
    phones = []
    for syllable in syllables:
        phones.extend(syllable.phones)
    characters = _celex_characters(celex)
    tokens = _align_celex(phones, characters)
    if tokens is None:
        m = f'cannot align celex column {celex!r} with disc {disc!r}'
        raise ParseError(m)
    for phone, (token, ambisyllabic) in zip(phones, tokens):
        phone.celex = token
        phone.ambisyllabic = ambisyllabic
    _check_cv(syllables, cv)
    return syllables


def _disc_syllables(disc):
    '''Build Syllable objects with Phone objects from the disc column.'''
    syllables = []
    for disc_syllable in re.split('[- ]', disc):
        if not disc_syllable: continue
        stress = 'weak'
        if disc_syllable.startswith("'"): stress = 'strong'
        elif disc_syllable.startswith('"'): stress = 'secondary'
        phones = [_make_phone(c) for c in disc_syllable.lstrip('\'"')]
        syllables.append(Syllable(phones=phones, stress=stress))
    return syllables


def _make_phone(disc_character):
    if disc_character not in disc_to_ipa:
        raise ParseError(f'unknown disc character {disc_character!r}')
    return Phone(disc=disc_character)


def _celex_characters(celex):
    '''Flatten a celex column into (character, ambisyllabic) pairs.
    Top level brackets delimit syllables; nested brackets mark an
    ambisyllabic phone that is written once but shared by two
    syllables.'''
    characters = []
    depth = 0
    for character in celex:
        if character == '[': depth += 1
        elif character == ']': depth -= 1
        elif character in '- ': continue
        else: characters.append((character, depth > 1))
    return characters


def _align_celex(phones, characters, phone_index=0, character_index=0):
    '''Align celex characters to phones, one token per phone.
    Tries longer tokens first and backtracks; a token must be a known
    celex symbol whose class matches the phone. Returns a list of
    (token, ambisyllabic) pairs, or None if no alignment exists.'''
    if phone_index == len(phones):
        if character_index == len(characters): return []
        return None
    wanted = phones[phone_index].phoneme_type
    for length in range(max_token_length, 0, -1):
        end = character_index + length
        if end > len(characters): continue
        token = ''.join(c for c, _ in characters[character_index:end])
        if celex_token_types.get(token) != wanted: continue
        rest = _align_celex(phones, characters, phone_index + 1, end)
        if rest is None: continue
        ambisyllabic = any(n for _, n in characters[character_index:end])
        return [(token, ambisyllabic)] + rest
    return None


def _check_cv(syllables, cv):
    '''The cv slots derived from the phones must match the cv column.'''
    derived = ''.join(syllable.cv for syllable in syllables)
    column = re.sub('[^CVS]', '', cv)
    if derived != column:
        m = f'cv mismatch: derived {derived!r}, column {column!r}'
        raise ParseError(m)


def _parse_english_line(parts, header):
    '''Parse an english line with one or more pronunciation groups.

    The first group becomes the returned Word, the other groups become
    Words in its pronunciations list. The pronounciation_count column
    is unreliable (48 lines declare more groups than are present), so
    the group count is derived from the number of fields.
    '''
    base = dict(zip(header[:5], parts[:5]))
    count = (len(parts) - 5) // 4
    words = []
    for i in range(count):
        status, disc, cv, celex = parts[5 + 4 * i:9 + 4 * i]
        try:
            syllables = parse_pronunciation(disc, cv, celex)
        except ParseError:
            continue
        fields = dict(base, disc=disc, cv=cv, celex=celex)
        words.append(_make_word(fields, header, syllables, 'english',
            status=status))
    if not words: return None
    word = words[0]
    word.pronunciations = words[1:]
    return word


def _make_word(fields, header, syllables, language, status=None):
    '''Build a Word from parsed fields; header[2] is the frequency.'''
    word = fields['word']
    return Word(word=word, id_number=int(fields['id_number']),
        id_number_lemma=int(fields['id_number_lemma']),
        frequency=int(fields[header[2]]), language=language,
        syllables=syllables, multiword=' ' in word,
        pronunciation_status=status, disc=fields['disc'],
        cv=fields['cv'], celex=fields['celex'])
