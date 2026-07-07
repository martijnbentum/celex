'''Extract syllable boundary training examples from CELEX.

A training example pairs the ipa phones of a word with per position
boundary labels, so a syllabifier can be trained on CELEX syllable
boundaries. The extraction is language generic; consumers map the ipa
symbols to their own phone set.
'''

from .parser import load


def word_to_example(word):
    '''Phones and boundary labels for one word.
    word:    a Word with phones and syllables

    Returns (phones, labels); phones is the list of ipa symbols and
    labels[i] is 1 when a syllable boundary follows phones[i], so
    len(labels) == len(phones) - 1. Ambisyllabic phones follow the
    disc column split: they count in the syllable that stores them.
    '''
    phones = [phone.ipa for phone in word.phones]
    labels = [0] * max(len(phones) - 1, 0)
    boundary = 0
    for syllable in word.syllables[:-1]:
        boundary += len(syllable.phones)
        if boundary == 0: continue
        labels[boundary - 1] = 1
    return phones, labels


def training_examples(language='dutch', multiword=False, words=None):
    '''Yield (phones, labels, word) triples for syllabifier training.
    language:     dutch, english or german
    multiword:    also yield entries containing spaces (default skip)
    words:        pre-loaded list of Word objects; omit to load(language)
    '''
    if words is None: words = load(language)
    for word in words:
        if word.multiword and not multiword: continue
        if not word.phones: continue
        phones, labels = word_to_example(word)
        yield phones, labels, word
