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
    'dutch': locations.dutch_header,
    'english': locations.english_header,
    'german': locations.german_header}

_lemma_paths = {
    'dutch': None,
    'english': None,
    'german': None,
}

_required_fields = {
    'dutch': ('id_number', 'id_number_lemma', 'word', 'disc', 'cv', 'celex'),
    'german': ('id_number', 'id_number_lemma', 'word', 'disc', 'cv', 'celex'),
}


def _celex_token_types():
    types = {}
    for token, ipa in celex_to_ipa.items():
        types[token] = phoneme_type(ipa)
    return types


celex_token_types = _celex_token_types()
max_token_length = max(len(token) for token in celex_token_types)


def load(language, verbose=True, bad_lines=None):
    '''Parse the phonology file of a language into Word objects.
    language:    dutch, english or german
    verbose:     print a summary of skipped entries
    bad_lines:   optional list collecting skipped line details
    '''
    if language not in languages:
        m = f'unknown language {language!r}, '
        m += "expected 'dutch', 'english' or 'german'"
        raise ValueError(m)
    header_path = languages[language]
    path = locations.word_form_path(language)
    header = header_path.read_text().split()
    words, skipped = [], 0
    with _open_celex_file(language, path, 'word-form') as fin:
        for line_number, line in enumerate(fin, start=1):
            text = line.rstrip('\n')
            word, error = _parse_line_with_error(text, header, language)
            if word is None:
                skipped += 1
                if bad_lines is not None:
                    bad_lines.append({'language': language,
                        'line_number': line_number, 'line': text,
                        'error': error})
            else:
                words.append(word)
    if verbose and skipped:
        print(f'skipped {skipped} {language} entries without a '
            'parsable pronunciation')
    for index, word in enumerate(words):
        word.index = index
    return words


def _missing_data_message(language, path, file_kind):
    m = f'CELEX {file_kind} file not found for {language}: {path}\n\n'
    m += 'Set the CELEX_DATA environment variable to the unzipped '
    m += 'CELEX-2 data directory, or place CELEX_DATA/ in the '
    m += 'repository root. Expected layout:\n\n'
    m += '  CELEX_DATA/\n'
    m += '    DUTCH/DPW/DPW.CD\n'
    m += '    DUTCH/DPL/DPL.CD\n'
    m += '    ENGLISH/EPW/EPW.CD\n'
    m += '    ENGLISH/EPL/EPL.CD\n'
    m += '    GERMAN/GPW/GPW.CD\n'
    m += '    GERMAN/GPL/GPL.CD\n\n'
    m += 'See README.md for setup instructions.'
    return m


def _open_celex_file(language, path, file_kind):
    if not path.exists():
        raise FileNotFoundError(_missing_data_message(language, path,
            file_kind))
    return open(path, encoding='latin-1')


def parse_line(line, header, language):
    '''Parse one data file line into a Word, or None on failure.'''
    word, _ = _parse_line_with_error(line, header, language)
    return word


def _parse_line_with_error(line, header, language):
    try:
        return _parse_line(line, header, language), None
    except ParseError as error:
        return None, str(error)
    except KeyError as error:
        return None, f'missing required column {error.args[0]!r}'
    except ValueError as error:
        return None, str(error)


def _parse_line(line, header, language):
    '''Parse one data file line into a Word. Raises ParseError on failure.'''
    parts = line.split('\\')
    if language == 'english': return _parse_english_line(parts, header)
    fields = dict(zip(header, parts))
    required = _required_fields.get(language, _required_fields['dutch'])
    for field in required:
        if field not in fields:
            raise ParseError(f'missing required column {field!r}')
    syllables = parse_pronunciation(fields['disc'], fields['cv'],
        fields['celex'])
    return _make_word(fields, header, syllables, language)


def parse_pronunciation(disc, cv, celex):
    '''Build Syllable objects from the three pronunciation columns.
    The cv and celex columns must use bracketed CELEX notation, e.g.
    [a:x][j@] and [VVC][CV]. Raises ParseError if a column is
    malformed or the columns cannot be aligned.'''
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


def _bracketed_characters(text, column_name):
    '''Flatten a bracketed column into (character, nested) pairs.
    Raises ParseError on unbalanced brackets or a character outside
    brackets.'''
    characters = []
    depth = 0
    for index, character in enumerate(text):
        if character == '[':
            depth += 1
        elif character == ']':
            depth -= 1
            if depth < 0:
                m = f'unmatched closing bracket in {column_name} '
                m += f'column {text!r} at position {index}'
                raise ParseError(m)
        elif character in '- ':
            continue
        elif depth == 0:
            m = f'character outside brackets in {column_name} '
            m += f'column {text!r} at position {index}'
            raise ParseError(m)
        else:
            characters.append((character, depth > 1))
    if depth:
        m = f'unclosed bracket in {column_name} column {text!r}'
        raise ParseError(m)
    return characters


def _celex_characters(celex):
    '''Flatten a celex column into (character, ambisyllabic) pairs.
    Top level brackets delimit syllables; nested brackets mark an
    ambisyllabic phone that is written once but shared by two
    syllables.'''
    return _bracketed_characters(celex, 'celex')


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
    column = _cv_slots(cv)
    if derived != column:
        m = f'cv mismatch: derived {derived!r}, column {column!r}'
        raise ParseError(m)


def _cv_slots(cv):
    '''Flatten a bracketed cv column into its C/V/S slots.'''
    slots = []
    for character, _ in _bracketed_characters(cv, 'cv'):
        if character not in 'CVS':
            m = f'unexpected character {character!r} in cv column {cv!r}'
            raise ParseError(m)
        slots.append(character)
    return ''.join(slots)


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
    errors = []
    for i in range(count):
        status, disc, cv, celex = parts[5 + 4 * i:9 + 4 * i]
        try:
            syllables = parse_pronunciation(disc, cv, celex)
        except ParseError as error:
            errors.append(str(error))
            continue
        fields = dict(base, disc=disc, cv=cv, celex=celex)
        words.append(_make_word(fields, header, syllables, 'english',
            status=status))
    if not words:
        if not errors: raise ParseError('no pronunciation groups found')
        m = 'no parsable english pronunciation'
        m += f': {"; ".join(errors)}'
        raise ParseError(m)
    word = words[0]
    word.pronunciations = words[1:]
    return word


def _make_word(fields, header, syllables, language, status=None):
    '''Build a Word from parsed fields; header[2] is the frequency.'''
    word = fields['word']
    return Word(word=word, id_number=_int_field(fields, 'id_number'),
        id_number_lemma=_int_field(fields, 'id_number_lemma'),
        frequency=_int_field(fields, header[2]), language=language,
        syllables=syllables, multiword=' ' in word,
        pronunciation_status=status, disc=fields['disc'],
        cv=fields['cv'], celex=fields['celex'])


def _int_field(fields, name):
    try:
        return int(fields[name])
    except KeyError:
        raise ParseError(f'missing required column {name!r}')
    except ValueError:
        raise ParseError(f'invalid integer in {name!r}: {fields[name]!r}')


def load_lemmas(language, verbose=True):
    '''Parse the phonology lemma file (DPL/EPL/GPL) into a {id: Word} dict.
    language:    dutch, english or german
    verbose:     print a summary of skipped entries
    '''
    if language not in _lemma_paths:
        raise ValueError(f'unknown language {language!r}')
    path = _lemma_paths[language] or locations.lemma_path(language)
    parsers = {
        'dutch':   _parse_dutch_lemma_line,
        'english': _parse_english_lemma_line,
        'german':  _parse_german_lemma_line,
    }
    lemmas, skipped = {}, 0
    with _open_celex_file(language, path, 'lemma') as fin:
        for line in fin:
            result = parsers[language](line.rstrip('\n'))
            if result is None:
                skipped += 1
            else:
                lemma_id, word = result
                lemmas[lemma_id] = word
    if verbose and skipped:
        print(f'skipped {skipped} {language} lemma entries without a '
            'parsable pronunciation')
    return lemmas


def _parse_dutch_lemma_line(line):
    '''DPL: IdNum / Head / Inl / PhonStrsDISC / PhonCVBr / PhonSylBCLX / ...'''
    parts = line.split('\\')
    if len(parts) < 6: return None
    try:
        lemma_id = int(parts[0])
        disc, cv, celex = parts[3], parts[4], parts[5]
        syllables = parse_pronunciation(disc, cv, celex)
    except (ValueError, ParseError):
        return None
    word = Word(word=parts[1], id_number=lemma_id, id_number_lemma=lemma_id,
        frequency=int(parts[2]) if parts[2].isdigit() else 0,
        language='dutch', syllables=syllables)
    return lemma_id, word


def _parse_german_lemma_line(line):
    '''GPL: IdNum / Head / Mann / PhonStrsDISC / PhonSylBCLX / ... / PhonCVBr / ...
    Field order differs from DPL: celex is field 4 (index 4), cv is field 8 (index 7).
    '''
    parts = line.split('\\')
    if len(parts) < 8: return None
    try:
        lemma_id = int(parts[0])
        disc, celex, cv = parts[3], parts[4], parts[7]
        syllables = parse_pronunciation(disc, cv, celex)
    except (ValueError, ParseError):
        return None
    word = Word(word=parts[1], id_number=lemma_id, id_number_lemma=lemma_id,
        frequency=int(parts[2]) if parts[2].isdigit() else 0,
        language='german', syllables=syllables)
    return lemma_id, word


def _parse_english_lemma_line(line):
    '''EPL: IdNum / Head / Cob / PronCnt / PronStatus / PhonStrsDISC / PhonCVBr / PhonSylBCLX ...
    Same multi-pronunciation layout as EPW but without IdNumLemma.
    '''
    parts = line.split('\\')
    if len(parts) < 8: return None
    try:
        lemma_id = int(parts[0])
        cob = int(parts[2]) if parts[2].isdigit() else 0
    except ValueError:
        return None
    count = (len(parts) - 4) // 4
    words = []
    for i in range(count):
        status, disc, cv, celex = parts[4 + 4 * i:8 + 4 * i]
        try:
            syllables = parse_pronunciation(disc, cv, celex)
        except ParseError:
            continue
        words.append(Word(word=parts[1], id_number=lemma_id,
            id_number_lemma=lemma_id, frequency=cob, language='english',
            syllables=syllables, pronunciation_status=status))
    if not words: return None
    word = words[0]
    word.pronunciations = words[1:]
    return lemma_id, word
