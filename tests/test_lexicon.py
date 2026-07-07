import pytest

from celex import Lexicon
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
    return languages['dutch'][1].read_text().split()


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


def test_lemma_none_without_lemma_file(small_lexicon):
    for word in small_lexicon.words:
        assert word.lemma is None


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
    # No lemmas loaded: family starts with self
    assert aagje_word.family == [aagje_word]


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
# repr
# ---------------------------------------------------------------------------

def test_lexicon_repr(small_lexicon):
    r = repr(small_lexicon)
    assert 'test' in r
    assert str(len(small_lexicon.words)) in r
