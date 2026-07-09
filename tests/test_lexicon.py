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


def test_word_index(small_lexicon):
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
# search_words
# ---------------------------------------------------------------------------

def test_search_words_orthographic(small_lexicon):
    results = small_lexicon.search_words(word='Aagje')
    assert len(results) == 1
    assert results[0].word == 'Aagje'


def test_search_words_ipa_spaced(small_lexicon):
    results_spaced = small_lexicon.search_words(ipa='aː x')
    results_plain  = small_lexicon.search_words(ipa='aːx')
    assert results_spaced == results_plain
    assert any(w.word == 'Aagje' for w in results_spaced)


def test_search_words_ipa_no_false_positives(small_lexicon):
    assert small_lexicon.search_words(ipa='zzz') == []


def test_search_words_stress_pattern(small_lexicon):
    results = small_lexicon.search_words(stress_pattern='s w')
    assert all(w.stress_pattern == 's w' for w in results)
    assert any(w.word == 'Aagje' for w in results)


def test_search_words_freq_range(small_lexicon):
    results = small_lexicon.search_words(freq_min=1, freq_max=10)
    assert all(1 <= w.frequency <= 10 for w in results)
    assert any(w.word == 'Aagje' for w in results)


def test_search_words_combined(small_lexicon):
    results = small_lexicon.search_words(stress_pattern='s w', freq_min=5)
    assert all(w.stress_pattern == 's w' and w.frequency >= 5
        for w in results)


def test_word_index_groups_homographs():
    header = dutch_header()
    duplicate = aagje.replace("5\\Aagje\\9\\5", "6\\Aagje\\3\\5")
    words = []
    for line in (aagje, aagtappel, duplicate):
        words.append(parse_line(line, header, 'dutch'))
    lexicon = Lexicon._from_words(words)
    assert [w.id_number for w in lexicon.word_index['Aagje']] == [5, 6]
    assert [w.word for w in lexicon.word_index['aagtappel']] == [
        'aagtappel']


def test_search_words_matches_linear_scan(small_lexicon):
    scan = [w for w in small_lexicon.words if w.word == 'aagtappel']
    assert small_lexicon.search_words(word='aagtappel') == scan


def test_search_words_miss_returns_empty(small_lexicon):
    assert small_lexicon.search_words(word='nope') == []
    assert 'nope' not in small_lexicon.word_index


def test_search_words_result_mutation_does_not_affect_index(small_lexicon):
    results = small_lexicon.search_words(word='Aagje')
    results.append('junk')
    words = small_lexicon.search_words(word='Aagje')
    assert [w.word for w in words] == ['Aagje']


# ---------------------------------------------------------------------------
# query API
# ---------------------------------------------------------------------------

def test_words_query_exact_label(small_lexicon):
    results = list(small_lexicon.words_query.filter(label='aagtappel'))
    assert [word.word for word in results] == ['aagtappel']


def test_words_query_label_contains(small_lexicon):
    exact = list(small_lexicon.words_query.filter(label='aagtappel'))
    contains = list(small_lexicon.words_query.filter(
        label__contains='aagtappel'))
    assert [word.word for word in exact] == ['aagtappel']
    assert [word.word for word in contains] == [
        'aagtappel', 'aagtappelen']


def test_query_numeric_lookup(small_lexicon):
    results = list(small_lexicon.words_query.filter(frequency__gte=1))
    assert all(word.frequency >= 1 for word in results)
    assert any(word.word == 'Aagje' for word in results)


def test_query_nested_list_relation(small_lexicon):
    results = list(small_lexicon.words_query.filter(
        syllables__label__contains='j ə'))
    assert [word.word for word in results] == ['Aagje']


def test_syllables_query_label_contains(small_lexicon):
    results = list(small_lexicon.syllables_query.filter(
        label__contains='aː'))
    assert all('aː' in syllable.label for syllable in results)
    assert len(results) > 0


def test_phones_query_exact_label(small_lexicon):
    results = list(small_lexicon.phones_query.filter(label='aː'))
    assert all(phone.label == 'aː' for phone in results)
    assert len(results) > 0


def test_query_get_and_get_or_none(small_lexicon):
    word = small_lexicon.words_query.get(label='Aagje')
    assert word.word == 'Aagje'
    assert small_lexicon.words_query.get_or_none(label='missing') is None


def test_query_get_raises_for_missing(small_lexicon):
    with pytest.raises(DoesNotExist):
        small_lexicon.words_query.get(label='missing')


def test_query_get_raises_for_multiple():
    header = dutch_header()
    duplicate = aagje.replace("5\\Aagje\\9\\5", "6\\Aagje\\3\\5")
    words = []
    for line in (aagje, duplicate):
        words.append(parse_line(line, header, 'dutch'))
    lexicon = Lexicon._from_words(words)
    with pytest.raises(MultipleObjectsReturned):
        lexicon.words_query.get(label='Aagje')


# ---------------------------------------------------------------------------
# search_syllables
# ---------------------------------------------------------------------------

def test_search_syllables_ipa(small_lexicon):
    results = small_lexicon.search_syllables(ipa='aː')
    assert all('aː' in s.ipa.replace(' ', '') for s in results)
    assert len(results) > 0


def test_search_syllables_stress(small_lexicon):
    results = small_lexicon.search_syllables(stress='strong')
    assert all(s.stress == 'strong' for s in results)
    assert all(s.stressed for s in results)


def test_search_syllables_combined(small_lexicon):
    results = small_lexicon.search_syllables(ipa='aː', stress='strong')
    assert all('aː' in s.ipa.replace(' ', '') and s.stress == 'strong'
        for s in results)


def test_search_syllables_no_match(small_lexicon):
    assert small_lexicon.search_syllables(stress='nonexistent') == []


# ---------------------------------------------------------------------------
# search_phones
# ---------------------------------------------------------------------------

def test_search_phones_ipa(small_lexicon):
    results = small_lexicon.search_phones(ipa='aː')
    assert all(p.ipa == 'aː' for p in results)
    assert len(results) > 0


def test_search_phones_position_onset(small_lexicon):
    results = small_lexicon.search_phones(position='onset')
    assert all(p.onset for p in results)
    assert len(results) > 0


def test_search_phones_position_nucleus(small_lexicon):
    results = small_lexicon.search_phones(position='nucleus')
    assert all(p.nucleus for p in results)


def test_search_phones_position_coda(small_lexicon):
    results = small_lexicon.search_phones(position='coda')
    assert all(p.coda for p in results)


def test_search_phones_invalid_position(small_lexicon):
    with pytest.raises(ValueError) as excinfo:
        small_lexicon.search_phones(position='word')
    message = str(excinfo.value)
    assert "unknown phone position 'word'" in message
    assert "'coda', 'nucleus', 'onset'" in message


def test_search_phones_ambisyllabic(small_lexicon):
    results = small_lexicon.search_phones(ambisyllabic=True)
    assert all(p.ambisyllabic for p in results)
    assert len(results) >= 1


def test_search_phones_stressed(small_lexicon):
    results = small_lexicon.search_phones(stressed=True)
    assert all(p.syllable.stressed for p in results)


def test_search_phones_unstressed(small_lexicon):
    results = small_lexicon.search_phones(stressed=False)
    assert all(not p.syllable.stressed for p in results)


def test_search_phones_combined(small_lexicon):
    results = small_lexicon.search_phones(position='onset', stressed=True)
    assert all(p.onset and p.syllable.stressed for p in results)


def test_search_phones_no_match(small_lexicon):
    assert small_lexicon.search_phones(ipa='zzz') == []


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
