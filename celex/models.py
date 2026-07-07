'''Object model for CELEX words, syllables and phones.

The hierarchy is a tree: each phone belongs to one syllable and each
syllable to one word. Ambisyllabic phones (nested brackets in the
source, e.g. [A[p]@l]) are stored in the following syllable's onset
and flagged; the surface_* properties expose the sharing without
breaking the tree.

Note for later: a richer alternative is a parallel timing tier in the
spirit of CV phonology, a word-level sequence of cv slots linked
many-to-many to phones. Ambisyllabicity and long vowels (one phone,
two V slots) then become links instead of flags. Such a tier could
exist in parallel to the current hierarchy without changing it: slots
would reference phones and leave the phone-syllable-word links as they
are. Not needed so far.
'''

from phone_mapper import disc_to_ipa, ipa_to_definition

from .utils import B, GR, R, RE


def phoneme_type(ipa):
    '''vowel, consonant or syllabic_consonant for an ipa symbol.'''
    definition = ipa_to_definition[ipa]
    if 'syllabic' in definition: return 'syllabic_consonant'
    if 'vowel' in definition or 'diphthong' in definition: return 'vowel'
    return 'consonant'


class Word:
    '''A word with its orthography, frequency and phonological structure.'''

    def __init__(self, word=None, id_number=None, id_number_lemma=None,
        frequency=None, language=None, syllables=None, multiword=False,
        pronunciation_status=None, disc=None, cv=None, celex=None):
        self.word = word
        self.id_number = id_number
        self.id_number_lemma = id_number_lemma
        self.frequency = frequency
        self.language = language
        self.multiword = multiword
        self.pronunciation_status = pronunciation_status
        self.disc = disc
        self.cv = cv
        self.celex = celex
        self.syllables = syllables if syllables else []
        self.pronunciations = []
        self.phones = []
        for index, syllable in enumerate(self.syllables):
            syllable.word = self
            syllable.index = index
            self.phones.extend(syllable.phones)
        for index, phone in enumerate(self.phones):
            phone.word = self
            phone.index = index

    def __repr__(self):
        m = f'{R}Word{RE} {B}word {RE}{self.word} | '
        m += f'{B}ipa {RE}{self.ipa} | '
        m += f'{B}stress {RE}{self.stress_pattern}'
        if self.language: m += f' {GR}{self.language}{RE}'
        return m

    @property
    def ipa(self):
        '''Space separated ipa symbols of all phones in the word.'''
        return ' '.join(phone.ipa for phone in self.phones)

    @property
    def stress_pattern(self):
        '''Space separated stress code per syllable: s, w or ss.'''
        codes = {'strong': 's', 'weak': 'w', 'secondary': 'ss'}
        return ' '.join(codes[s.stress] for s in self.syllables)


class Syllable:
    '''A syllable holding phones, with stress and structure properties.'''

    def __init__(self, phones=None, stress='weak'):
        self.phones = phones if phones else []
        self.stress = stress
        self.word = None
        self.index = None
        for phone in self.phones:
            phone.syllable = self

    def __repr__(self):
        m = f'{R}Syllable{RE} {B}ipa {RE}{self.ipa} | '
        m += f'{B}stress {RE}{self.stress}'
        return m

    @property
    def ipa(self):
        '''Space separated ipa symbols of the phones in this syllable.'''
        return ' '.join(phone.ipa for phone in self.phones)

    @property
    def disc(self):
        return ''.join(phone.disc for phone in self.phones)

    @property
    def celex(self):
        return ''.join(phone.celex for phone in self.phones)

    @property
    def cv(self):
        return ''.join(phone.cv for phone in self.phones)

    @property
    def stressed(self):
        return self.stress in ('strong', 'secondary')

    @property
    def prev(self):
        '''The previous syllable in the word, None at the word start.'''
        if self.word is None or not self.index: return None
        return self.word.syllables[self.index - 1]

    @property
    def next(self):
        '''The next syllable in the word, None at the word end.'''
        if self.word is None or self.index is None: return None
        if self.index + 1 >= len(self.word.syllables): return None
        return self.word.syllables[self.index + 1]

    @property
    def nucleus(self):
        '''The phones that form the syllable nucleus.'''
        return [phone for phone in self.phones if phone.nucleus]

    @property
    def onset(self):
        '''The phones before the nucleus.'''
        nucleus = self.nucleus
        if not nucleus: return list(self.phones)
        return self.phones[:self.phones.index(nucleus[0])]

    @property
    def coda(self):
        '''The phones after the nucleus.'''
        nucleus = self.nucleus
        if not nucleus: return []
        return self.phones[self.phones.index(nucleus[-1]) + 1:]

    @property
    def rhyme(self):
        '''The nucleus and coda phones.'''
        return self.nucleus + self.coda

    @property
    def weight(self):
        '''light, heavy or superheavy, from the cv slots in the rhyme
        (the onset is weightless). None for the rare syllable without
        a nucleus, e.g. pst.'''
        return self._slot_weight(self.rhyme)

    @property
    def surface_phones(self):
        '''The phones of this syllable plus an ambisyllabic phone
        shared from the next syllable's onset, e.g. the p in [A[p]@l].'''
        return self.phones + self._shared_phones()

    @property
    def surface_rhyme(self):
        '''The rhyme plus shared ambisyllabic phones, which close the
        syllable.'''
        return self.rhyme + self._shared_phones()

    @property
    def surface_weight(self):
        '''weight with shared ambisyllabic phones counted in the coda,
        so the p in [A[p]@l] makes the first syllable heavy.'''
        return self._slot_weight(self.surface_rhyme)

    def _shared_phones(self):
        '''Ambisyllabic phones in the next syllable's onset.'''
        following = self.next
        if following is None: return []
        shared = []
        for phone in following.onset:
            if phone.ambisyllabic: shared.append(phone)
        return shared

    def _slot_weight(self, phones):
        if not phones: return None
        slots = len(''.join(phone.cv for phone in phones))
        if slots == 1: return 'light'
        if slots == 2: return 'heavy'
        return 'superheavy'


class Phone:
    '''A single phone linked to its syllable and word.'''

    def __init__(self, disc=None, celex=None, ambisyllabic=False):
        self.disc = disc
        self.celex = celex
        self.ipa = disc_to_ipa[disc]
        self.ambisyllabic = ambisyllabic
        self.syllable = None
        self.word = None
        self.index = None

    def __repr__(self):
        m = f'{R}Phone{RE} {B}ipa {RE}{self.ipa} | '
        m += f'{B}disc {RE}{self.disc} | '
        m += f'{B}type {RE}{self.phoneme_type}'
        return m

    @property
    def phoneme_type(self):
        '''vowel, consonant or syllabic_consonant, from the ipa definition.'''
        return phoneme_type(self.ipa)

    @property
    def cv(self):
        '''The cv slots this phone occupies: C, S, V or VV.'''
        if self.phoneme_type == 'syllabic_consonant': return 'S'
        if self.phoneme_type == 'consonant': return 'C'
        definition = ipa_to_definition[self.ipa]
        if 'long' in definition or 'diphthong' in definition: return 'VV'
        return 'V'

    @property
    def prev(self):
        '''The previous phone in the word, None at the word start.'''
        if self.word is None or not self.index: return None
        return self.word.phones[self.index - 1]

    @property
    def next(self):
        '''The next phone in the word, None at the word end.'''
        if self.word is None or self.index is None: return None
        if self.index + 1 >= len(self.word.phones): return None
        return self.word.phones[self.index + 1]

    @property
    def surface_syllables(self):
        '''The syllables this phone belongs to: two when ambisyllabic
        (the preceding syllable first), otherwise one.'''
        if self.syllable is None: return []
        if self.ambisyllabic and self.syllable.prev is not None:
            return [self.syllable.prev, self.syllable]
        return [self.syllable]

    @property
    def nucleus(self):
        '''Whether this phone is part of the syllable nucleus.'''
        return self.phoneme_type in ('vowel', 'syllabic_consonant')

    @property
    def onset(self):
        '''Whether this phone is part of the syllable onset.'''
        if self.syllable is None: return False
        return self in self.syllable.onset

    @property
    def coda(self):
        '''Whether this phone is part of the syllable coda.'''
        if self.syllable is None: return False
        return self in self.syllable.coda
