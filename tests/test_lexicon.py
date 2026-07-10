import pytest

from celex import DoesNotExist, Lexicon, MultipleObjectsReturned
from celex.parser import _parse_dutch_lemma_line, languages, parse_line


# ---------------------------------------------------------------------------
# Shared test words (same strings as in test_celex.py)
# ---------------------------------------------------------------------------

aagje       = "5\\Aagje\\9\\5\\'ax-j@\\[VVC][CV]\\[a:x][j@]"
aagtappel   = "7\\aagtappel\\0\\7\\'axt-A-p@l\\[VVCC][V[C]VC]\\[a:xt][A[p]@l]"
aagtappelen = "8\\aagtappelen\\0\\7\\'axt-A-p@-l@\\[VVCC][V[C]V][CV]\\[a:xt][A[p]@][l@]"
aap_na      = "5514\\aap na\\0\\65134\\'ap 'na\\[VVC] [CVV]\\[a:p] [na:]"

# DPL lemma lines for DPW ids 5 (Aagje) and 7 (aagtappel)
dpl_aagje     = ("5\\Aagje\\9\\'ax-j@\\[VVC][CV]\\[a:x][j@]\\'ax-j@"
    "\\[VVC][CV]\\[a:x][j@]\\\\")
dpl_aagtappel = ("7\\aagtappel\\0\\'axt-A-p@l\\[VVCC][V[C]VC]\\[a:xt][A[p]@l]"
    "\\'axt-A-p@l\\[VVCC][V[C]VC]\\[a:xt][A[p]@l]\\a:xt#A-p@l\\a:xt#A.p@l")


def dutch_header():
    return languages['dutch'].read_text().split()


def _make_words():
    header = dutch_header()
    words = []
    for line in (aagje, aagtappel, aagtappelen, aap_na):
        w = parse_line(line, header, 'dutch')
        if w:
            words.append(w)
    return words


def _make_lemmas():
    lemmas = {}
    for line in (dpl_aagje, dpl_aagtappel):
        result = _parse_dutch_lemma_line(line)
        if result:
            lemmas[result[0]] = result[1]
    return lemmas


@pytest.fixture(scope='module')
def small_lexicon():
    '''Lexicon without loaded lemma file — lemma is None for all words.'''
    return Lexicon._from_words(_make_words())


@pytest.fixture(scope='module')
def small_lexicon_with_lemmas():
    '''Lexicon with hand-parsed DPL entries for lemma tests.'''
    return Lexicon._from_words(_make_words(), lemmas=_make_lemmas())


# ---------------------------------------------------------------------------
# Linking: lexicon, index, prev, next
# ---------------------------------------------------------------------------

def test_words_linked_to_lexicon(small_lexicon):
    for word in small_lexicon.words:
        assert word.lexicon is small_lexicon


def test_lexicon_collects_bad_celex_lines(monkeypatch):
    import celex.lexicon

    def fake_load(language, bad_lines=None, use_cache=True):
        if bad_lines is not None:
            bad_lines.append({'language': language, 'line_number': 7,
                'line': 'bad', 'error': 'empty pronunciation'})
        return _make_words()[:1]

    monkeypatch.setattr(celex.lexicon, 'load', fake_load)
    monkeypatch.setattr(celex.lexicon, 'load_lemmas', lambda language,
        verbose=False, use_cache=True: {})
    lexicon = Lexicon('dutch')
    assert lexicon.bad_celex_lines == [{'language': 'dutch',
        'line_number': 7, 'line': 'bad', 'error': 'empty pronunciation'}]
    lexicon.bad_celex_lines.append({'language': 'dutch'})
    assert len(lexicon.bad_celex_lines) == 1


def test_word_file_order_index(small_lexicon):
    for i, word in enumerate(small_lexicon.words):
        assert word.index == i


def test_word_prev_next(small_lexicon):
    words = small_lexicon.words
    assert words[0].prev is None
    assert words[0].next is words[1]
    assert words[1].prev is words[0]
    assert words[-1].next is None


# ---------------------------------------------------------------------------
# Lemma (DPL → DPW linking)
# ---------------------------------------------------------------------------

def test_lemma_is_dpl_object(small_lexicon_with_lemmas):
    w = next(w for w in small_lexicon_with_lemmas.words if w.word == 'Aagje')
    assert w.lemma is not None
    assert w.lemma.word == 'Aagje'
    assert w.lemma is not w     # DPL entry is a different object from DPW


def test_lemma_head_form(small_lexicon_with_lemmas):
    form = next(w for w in small_lexicon_with_lemmas.words
        if w.word == 'aagtappelen')
    assert form.lemma is not None
    assert form.lemma.word == 'aagtappel'


def test_lemma_has_phonology(small_lexicon_with_lemmas):
    w = next(w for w in small_lexicon_with_lemmas.words if w.word == 'Aagje')
    assert w.lemma.ipa == 'aː x j ə'
    assert w.lemma.disc == "'ax-j@"
    assert w.lemma.cv == '[VVC][CV]'
    assert w.lemma.celex == '[a:x][j@]'
    assert w.lemma.stress_pattern == 's w'
    assert w.lemma.key == 'dutch:lemma:5:p0'


def test_lemma_none_without_lemma_file(small_lexicon):
    for word in small_lexicon.words:
        assert word.lemma is None


def test_missing_lemma_file_warns(monkeypatch, tmp_path):
    import celex.parser

    lexicon = Lexicon._from_words(_make_words())
    missing = tmp_path / 'missing' / 'DPL.CD'
    monkeypatch.setitem(celex.parser._lemma_paths, 'test', missing)
    with pytest.warns(RuntimeWarning) as warnings:
        lexicon._link_lemmas()
    message = str(warnings[0].message)
    assert 'CELEX lemma file not found for test' in message
    assert 'word.lemma and word.family will be None' in message
    assert all(word.lemma is None for word in lexicon.words)
    assert all(word.family is None for word in lexicon.words)


# ---------------------------------------------------------------------------
# Siblings
# ---------------------------------------------------------------------------

def test_siblings_exclude_self(small_lexicon):
    base = next(w for w in small_lexicon.words if w.word == 'aagtappel')
    form = next(w for w in small_lexicon.words if w.word == 'aagtappelen')
    assert base not in base.siblings
    assert form in base.siblings
    assert form not in form.siblings
    assert base in form.siblings


def test_siblings_empty_for_unique_lemma_group(small_lexicon):
    aagje_word = next(w for w in small_lexicon.words if w.word == 'Aagje')
    assert aagje_word.siblings == []


# ---------------------------------------------------------------------------
# family property
# ---------------------------------------------------------------------------

def test_family_no_lemma_file(small_lexicon):
    aagje_word = next(w for w in small_lexicon.words if w.word == 'Aagje')
    assert aagje_word.family is None


def test_family_lemma_first(small_lexicon_with_lemmas):
    form = next(w for w in small_lexicon_with_lemmas.words
        if w.word == 'aagtappelen')
    assert form.family[0] is form.lemma
    assert form.family[0].word == 'aagtappel'
    assert form.family[1] is form


def test_family_includes_siblings(small_lexicon_with_lemmas):
    base = next(w for w in small_lexicon_with_lemmas.words
        if w.word == 'aagtappel')
    form = next(w for w in small_lexicon_with_lemmas.words
        if w.word == 'aagtappelen')
    assert form in base.family


def test_family_lemma_plus_self_only_when_no_siblings(small_lexicon_with_lemmas):
    aagje_word = next(w for w in small_lexicon_with_lemmas.words
        if w.word == 'Aagje')
    fam = aagje_word.family
    assert fam[0] is aagje_word.lemma
    assert fam[1] is aagje_word
    assert len(fam) == 2


def test_siblings_ignore_non_positive_lemma_ids():
    lexicon = Lexicon._from_words(_make_words())
    word, sibling = lexicon.words[:2]
    word.id_number_lemma = 0
    sibling.id_number_lemma = 0
    lexicon._link_siblings()
    assert word.siblings == []
    assert sibling.siblings == []


# ---------------------------------------------------------------------------
# query API
# ---------------------------------------------------------------------------

def test_query_words_exact_label(small_lexicon):
    results = list(small_lexicon.query.words.filter(label='aagtappel'))
    assert [word.word for word in results] == ['aagtappel']


def test_query_namespace_cached(small_lexicon):
    assert small_lexicon.query is small_lexicon.query
    assert small_lexicon.query.words is small_lexicon.query.words
    assert small_lexicon.query.syllables is small_lexicon.query.syllables
    assert small_lexicon.query.phones is small_lexicon.query.phones


def test_query_words_label_contains(small_lexicon):
    exact = list(small_lexicon.query.words.filter(label='aagtappel'))
    contains = list(small_lexicon.query.words.filter(
        label__contains='aagtappel'))
    assert [word.word for word in exact] == ['aagtappel']
    assert [word.word for word in contains] == [
        'aagtappel', 'aagtappelen']


def test_query_words_ipa_contains(small_lexicon):
    results = list(small_lexicon.query.words.filter(ipa__contains='aː x'))
    assert any(word.word == 'Aagje' for word in results)


def test_query_numeric_lookup(small_lexicon):
    results = list(small_lexicon.query.words.filter(frequency__gte=1))
    assert all(word.frequency >= 1 for word in results)
    assert any(word.word == 'Aagje' for word in results)


def test_query_combined_lookups(small_lexicon):
    results = list(small_lexicon.query.words.filter(
        stress_pattern='s w', frequency__gte=5))
    assert all(word.stress_pattern == 's w' and word.frequency >= 5
        for word in results)


def test_query_nested_list_relation(small_lexicon):
    results = list(small_lexicon.query.words.filter(
        syllables__label__contains='j ə'))
    assert [word.word for word in results] == ['Aagje']


def test_query_terminal_list_exact(small_lexicon):
    word = small_lexicon.words[0]
    results = list(small_lexicon.query.words.filter(
        syllables=word.syllables))
    assert results == [word]


def test_query_terminal_list_exact_requires_list(small_lexicon):
    with pytest.raises(ValueError) as excinfo:
        list(small_lexicon.query.words.filter(syllables='x'))
    assert 'exact lookup on a list value expects a list' in str(excinfo.value)


def test_query_list_contains(small_lexicon):
    word = small_lexicon.words[0]
    syllable = word.syllables[0]
    results = list(small_lexicon.query.words.filter(
        syllables__contains=syllable))
    assert results == [word]


def test_query_list_len(small_lexicon):
    results = list(small_lexicon.query.words.filter(syllables__len=2))
    assert all(len(word.syllables) == 2 for word in results)
    assert any(word.word == 'Aagje' for word in results)


def test_query_syllables_label_contains(small_lexicon):
    results = list(small_lexicon.query.syllables.filter(
        label__contains='aː'))
    assert all('aː' in syllable.label for syllable in results)
    assert len(results) > 0


def test_query_syllables_stress(small_lexicon):
    results = list(small_lexicon.query.syllables.filter(stress='strong'))
    assert all(syllable.stress == 'strong' for syllable in results)
    assert all(syllable.stressed for syllable in results)


def test_query_syllables_no_match(small_lexicon):
    assert list(small_lexicon.query.syllables.filter(
        stress='nonexistent')) == []


def test_query_phones_exact_label(small_lexicon):
    results = list(small_lexicon.query.phones.filter(label='aː'))
    assert all(phone.label == 'aː' for phone in results)
    assert len(results) > 0


def test_query_phones_position(small_lexicon):
    results = list(small_lexicon.query.phones.filter(position='onset'))
    assert all(phone.position == 'onset' for phone in results)
    assert all(phone.onset for phone in results)
    assert len(results) > 0


def test_query_phones_ambisyllabic(small_lexicon):
    results = list(small_lexicon.query.phones.filter(ambisyllabic=True))
    assert all(phone.ambisyllabic for phone in results)
    assert len(results) >= 1


def test_query_phones_stressed(small_lexicon):
    results = list(small_lexicon.query.phones.filter(stressed=True))
    assert all(phone.stressed for phone in results)


def test_query_phones_unstressed(small_lexicon):
    results = list(small_lexicon.query.phones.filter(stressed=False))
    assert all(not phone.stressed for phone in results)


def test_query_phones_combined(small_lexicon):
    results = list(small_lexicon.query.phones.filter(
        position='onset', stressed=True))
    assert all(phone.position == 'onset' and phone.stressed
        for phone in results)


def test_query_phones_no_match(small_lexicon):
    assert list(small_lexicon.query.phones.filter(ipa='zzz')) == []


def test_query_get_and_get_or_none(small_lexicon):
    word = small_lexicon.query.words.get(label='Aagje')
    assert word.word == 'Aagje'
    assert small_lexicon.query.words.get_or_none(label='missing') is None


def test_query_get_raises_for_missing(small_lexicon):
    with pytest.raises(DoesNotExist):
        small_lexicon.query.words.get(label='missing')


def test_query_get_raises_for_multiple():
    header = dutch_header()
    duplicate = aagje.replace("5\\Aagje\\9\\5", "6\\Aagje\\3\\5")
    words = []
    for line in (aagje, duplicate):
        words.append(parse_line(line, header, 'dutch'))
    lexicon = Lexicon._from_words(words)
    with pytest.raises(MultipleObjectsReturned):
        lexicon.query.words.get(label='Aagje')


# ---------------------------------------------------------------------------
# syllables and phones properties
# ---------------------------------------------------------------------------

def test_syllables_flat_list(small_lexicon):
    expected = [s for w in small_lexicon.words for s in w.syllables]
    assert small_lexicon.syllables == expected


def test_syllables_cached(small_lexicon):
    assert small_lexicon.syllables is small_lexicon.syllables


def test_phones_flat_list(small_lexicon):
    expected = [p for w in small_lexicon.words for p in w.phones]
    assert small_lexicon.phones == expected


def test_phones_cached(small_lexicon):
    assert small_lexicon.phones is small_lexicon.phones


def test_syllables_word_membership(small_lexicon):
    for syllable in small_lexicon.syllables:
        assert syllable in syllable.word.syllables


def test_phones_word_membership(small_lexicon):
    for phone in small_lexicon.phones:
        assert phone in phone.word.phones


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

def test_lexicon_repr(small_lexicon):
    r = repr(small_lexicon)
    assert 'test' in r
    assert str(len(small_lexicon.words)) in r
