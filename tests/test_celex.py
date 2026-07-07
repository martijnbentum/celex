import pytest

from celex import ParseError, parse_line, parse_pronunciation
from celex.parser import languages


def read_header(language):
    return languages[language][1].read_text().split()


@pytest.fixture(scope='module')
def dutch_header():
    return read_header('dutch')


@pytest.fixture(scope='module')
def english_header():
    return read_header('english')


@pytest.fixture(scope='module')
def german_header():
    return read_header('german')


aagje = "5\\Aagje\\9\\5\\'ax-j@\\[VVC][CV]\\[a:x][j@]"
aagtappel = "7\\aagtappel\\0\\7\\'axt-A-p@l\\[VVCC][V[C]VC]\\[a:xt][A[p]@l]"
aap_na = "5514\\aap na\\0\\65134\\'ap 'na\\[VVC] [CVV]\\[a:p] [na:]"
aafje = '3\\Aafje\\41\\3\\\\\\'
plaats = "297051\\plaats\\1962\\61024\\'plats\\[CCVVCC]\\[pla:ts]"
aas = '7\\AAs\\0\\5\\1\\P\\"1-\'1z\\[VV][VVC]\\[eI][eIz]'
bottle = "9031\\bottle\\1479\\4837\\1\\P\\'bQ-tP\\[CV][CS]\\[bO][tl,]"
rhythm = ("74336\\rhythm\\332\\38823\\4\\P\\'rI-D@m\\[CV][CVC]\\[rI][D@m]"
    "\\P\\'rI-DF\\[CV][CS]\\[rI][Dm,]\\S\\'rI-T@m\\[CV][CVC]\\[rI][T@m]"
    "\\S\\'rI-TF\\[CV][CS]\\[rI][Tm,]")
abbestellen = ('3\\abbestellen\\1\\35\\\'&p-b@-StE-l@n\\[ap][b@][StE[l]@n]'
    '\\[VC][CV][CCV[C]VC]')
annonciere = ("13\\annonciere\\0\\182\\&-n~-'si-r@\\[a[n]O~:][si:][r@]"
    "\\[V[C]VV][CVV][CV]")
pst = "247576\\pst\\15\\81791\\'pst\\[CCC]\\[pst]"


def test_import():
    import celex
    assert celex is not None


def test_word_attributes(dutch_header):
    word = parse_line(aagje, dutch_header, 'dutch')
    assert word.word == 'Aagje'
    assert word.id_number == 5
    assert word.id_number_lemma == 5
    assert word.frequency == 9
    assert word.language == 'dutch'
    assert word.multiword is False
    assert word.disc == "'ax-j@"
    assert word.ipa == 'aː x j ə'
    assert word.stress_pattern == 's w'
    assert len(word.syllables) == 2
    assert len(word.phones) == 4


def test_syllable_attributes(dutch_header):
    word = parse_line(aagje, dutch_header, 'dutch')
    first, second = word.syllables
    assert first.stress == 'strong' and first.stressed
    assert second.stress == 'weak' and not second.stressed
    assert first.ipa == 'aː x'
    assert first.disc == 'ax'
    assert first.celex == 'a:x'
    assert first.cv == 'VVC'
    assert first.word is word
    assert (first.index, second.index) == (0, 1)


def test_syllable_structure(dutch_header):
    word = parse_line(aagje, dutch_header, 'dutch')
    syllable = word.syllables[0]
    assert [p.disc for p in syllable.onset] == []
    assert [p.disc for p in syllable.nucleus] == ['a']
    assert [p.disc for p in syllable.coda] == ['x']
    assert [p.disc for p in syllable.rhyme] == ['a', 'x']
    syllable = word.syllables[1]
    assert [p.disc for p in syllable.onset] == ['j']
    assert [p.disc for p in syllable.coda] == []


def test_syllable_weight(dutch_header):
    '''Weight counts the cv slots in the rhyme, the onset is
    weightless: 1 slot light, 2 heavy, 3 or more superheavy.'''
    word = parse_line(aagje, dutch_header, 'dutch')
    assert word.syllables[0].weight == 'superheavy'    # a:x = VV C
    assert word.syllables[1].weight == 'light'         # j@, rhyme @ = V
    word = parse_line(aagtappel, dutch_header, 'dutch')
    assert word.syllables[1].weight == 'light'         # A = V
    assert word.syllables[2].weight == 'heavy'         # p@l, rhyme @l
    word = parse_line(pst, dutch_header, 'dutch')
    assert word.syllables[0].weight is None            # no nucleus


def test_syllabic_consonant_weight(english_header):
    word = parse_line(bottle, english_header, 'english')
    assert word.syllables[1].weight == 'light'         # tP, rhyme S


def test_phone_attributes(dutch_header):
    word = parse_line(aagje, dutch_header, 'dutch')
    phone = word.phones[0]
    assert phone.disc == 'a'
    assert phone.celex == 'a:'
    assert phone.ipa == 'aː'
    assert phone.phoneme_type == 'vowel'
    assert phone.cv == 'VV'
    assert phone.word is word
    assert phone.syllable is word.syllables[0]
    assert phone.nucleus and not phone.onset and not phone.coda
    coda = word.phones[1]
    assert coda.phoneme_type == 'consonant'
    assert coda.cv == 'C'
    assert coda.coda and not coda.onset and not coda.nucleus


def test_phone_prev_next(dutch_header):
    word = parse_line(aagje, dutch_header, 'dutch')
    assert word.phones[0].prev is None
    assert word.phones[0].next is word.phones[1]
    assert word.phones[1].prev is word.phones[0]
    assert word.phones[-1].next is None
    assert word.phones[1].next.syllable is word.syllables[1]


def test_ambisyllabic(dutch_header):
    word = parse_line(aagtappel, dutch_header, 'dutch')
    flags = [p.ambisyllabic for p in word.phones]
    assert flags == [False, False, False, False, True, False, False]
    phone = word.phones[4]
    assert phone.disc == 'p'
    assert phone.syllable.index == 2
    assert phone.onset


def test_surface_phones_and_weight(dutch_header, german_header):
    word = parse_line(aagtappel, dutch_header, 'dutch')
    first, second, third = word.syllables
    assert [p.disc for p in second.phones] == ['A']
    assert [p.disc for p in second.surface_phones] == ['A', 'p']
    assert [p.disc for p in second.surface_rhyme] == ['A', 'p']
    assert second.weight == 'light'
    assert second.surface_weight == 'heavy'
    assert first.surface_phones == first.phones
    assert first.surface_weight == first.weight
    assert third.surface_phones == third.phones
    shared = word.phones[4]
    assert shared.surface_syllables == [second, third]
    assert word.phones[0].surface_syllables == [first]
    word = parse_line(abbestellen, german_header, 'german')
    syllable = word.syllables[2]
    assert syllable.disc == 'StE'
    assert syllable.weight == 'light'
    assert syllable.surface_weight == 'heavy'


def test_timing_tier(dutch_header):
    word = parse_line(aagtappel, dutch_header, 'dutch')
    tier = word.timing
    assert tier is word.timing
    assert tier.word is word
    assert tier.pattern == 'VVCCVCVC'
    assert [slot.index for slot in tier.slots] == list(range(8))
    long_vowel = word.phones[0]
    slots = tier.phone_to_slots(long_vowel)
    assert len(slots) == 2
    assert slots[0].phone is slots[1].phone
    assert (slots[0].kind, slots[1].kind) == ('V', 'V')
    shared = word.phones[4]
    slots = tier.phone_to_slots(shared)
    assert len(slots) == 1
    assert slots[0].syllables == word.syllables[1:]
    assert tier.slots[0].syllables == [word.syllables[0]]


def test_timing_tier_syllabic_consonant(english_header):
    word = parse_line(bottle, english_header, 'english')
    assert word.timing.pattern == 'CVCS'
    assert word.timing.slots[-1].phone.ipa == 'l̩'


def test_multiword(dutch_header):
    word = parse_line(aap_na, dutch_header, 'dutch')
    assert word.multiword is True
    assert word.stress_pattern == 's s'
    assert len(word.syllables) == 2
    assert word.ipa == 'aː p n aː'


def test_empty_pronunciation_skipped(dutch_header):
    assert parse_line(aafje, dutch_header, 'dutch') is None


def test_affricate_versus_cluster(dutch_header):
    '''ts in plaats is t plus s, disc decides the tokenization.'''
    word = parse_line(plaats, dutch_header, 'dutch')
    assert [p.celex for p in word.phones] == [
        'p', 'l', 'a:', 't', 's']


def test_secondary_stress(english_header):
    word = parse_line(aas, english_header, 'english')
    assert word.stress_pattern == 'ss s'
    assert [s.stress for s in word.syllables] == ['secondary', 'strong']


def test_syllabic_consonant(english_header):
    word = parse_line(bottle, english_header, 'english')
    phone = word.phones[-1]
    assert phone.disc == 'P'
    assert phone.celex == 'l,'
    assert phone.ipa == 'l̩'
    assert phone.phoneme_type == 'syllabic_consonant'
    assert phone.cv == 'S'
    assert phone.nucleus
    assert [p.ipa for p in phone.syllable.rhyme] == ['l̩']


def test_english_pronunciation_variants(english_header):
    word = parse_line(rhythm, english_header, 'english')
    assert word.pronunciation_status == 'P'
    assert word.ipa == 'r ɪ ð ə m'
    assert len(word.pronunciations) == 3
    variant = word.pronunciations[0]
    assert variant.pronunciation_status == 'P'
    assert variant.ipa == 'r ɪ ð m̩'
    assert variant.word == 'rhythm'
    assert variant.pronunciations == []


def test_german_ambisyllabic(german_header):
    word = parse_line(abbestellen, german_header, 'german')
    ambisyllabic = [p for p in word.phones if p.ambisyllabic]
    assert [p.disc for p in ambisyllabic] == ['l']
    assert word.stress_pattern == 's w w w'


def test_german_nasal_vowel(german_header):
    word = parse_line(annonciere, german_header, 'german')
    phone = word.phones[2]
    assert phone.disc == '~'
    assert phone.celex == 'O~:'
    assert phone.ipa == 'ɒ̃ː'
    assert phone.cv == 'VV'


def test_misaligned_columns_raise():
    with pytest.raises(ParseError):
        parse_pronunciation("'grunt", '[CCVCC]', '[grunt]')
    with pytest.raises(ParseError):
        parse_pronunciation('', '', '')
    with pytest.raises(ParseError):
        parse_pronunciation("'ri-@b", '[CV][VC]', '[ri:][@b]')


def test_load_language_validation():
    from celex import load
    with pytest.raises(ValueError):
        load('french')
