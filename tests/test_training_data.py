import pytest

from celex import parse_line
from celex.parser import languages
from celex.training_data import training_examples, word_to_example


def read_header(language):
    return languages[language][1].read_text().split()


@pytest.fixture(scope='module')
def dutch_header():
    return read_header('dutch')


aagje = "5\\Aagje\\9\\5\\'ax-j@\\[VVC][CV]\\[a:x][j@]"
aagtappel = "7\\aagtappel\\0\\7\\'axt-A-p@l\\[VVCC][V[C]VC]\\[a:xt][A[p]@l]"
aap_na = "5514\\aap na\\0\\65134\\'ap 'na\\[VVC] [CVV]\\[a:p] [na:]"
plaats = "297051\\plaats\\1962\\61024\\'plats\\[CCVVCC]\\[pla:ts]"


def test_word_to_example(dutch_header):
    word = parse_line(aagje, dutch_header, 'dutch')
    phones, labels = word_to_example(word)
    assert phones == ['aː', 'x', 'j', 'ə']
    assert labels == [0, 1, 0]


def test_word_to_example_ambisyllabic(dutch_header):
    word = parse_line(aagtappel, dutch_header, 'dutch')
    phones, labels = word_to_example(word)
    assert phones == ['aː', 'x', 't', 'ɑ', 'p', 'ə', 'l']
    # the ambisyllabic p is stored in the last syllable: aːxt-ɑ-pəl
    assert labels == [0, 0, 1, 1, 0, 0]


def test_word_to_example_monosyllable(dutch_header):
    word = parse_line(plaats, dutch_header, 'dutch')
    phones, labels = word_to_example(word)
    assert phones == ['p', 'l', 'aː', 't', 's']
    assert labels == [0, 0, 0, 0]


def test_training_examples_skips_multiword(dutch_header):
    words = [parse_line(line, dutch_header, 'dutch')
        for line in (aagje, aap_na, plaats)]
    examples = list(training_examples(words=words))
    assert [word.word for _, _, word in examples] == ['Aagje', 'plaats']
    examples = list(training_examples(words=words, multiword=True))
    assert [word.word for _, _, word in examples] == ['Aagje', 'aap na',
        'plaats']


def test_training_examples_yields_labels(dutch_header):
    words = [parse_line(aagje, dutch_header, 'dutch')]
    phones, labels, word = next(training_examples(words=words))
    assert (phones, labels) == word_to_example(word)
