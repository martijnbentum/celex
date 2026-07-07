'''The cv timing tier as a parallel structure over the word hierarchy.

Slots hold references into the phone-syllable-word tree, but the tree
holds no references back: the tier is a derived view built from the
per phone cv slots and can never disagree with the tree. The
many-to-many linking runs in two orthogonal directions: length is
phone to slots (a long vowel or diphthong is one phone linked to two
V slots) and ambisyllabicity is slot to syllables (a shared consonant
is one slot linked to two syllable nodes).
'''

from .utils import B, R, RE


class TimingTier:
    '''The cv tier of one word: slots linked many-to-one to phones.'''

    def __init__(self, word):
        self.word = word
        self.slots = []
        for phone in word.phones:
            for kind in phone.cv:
                self.slots.append(Slot(kind, phone, len(self.slots)))

    def __repr__(self):
        m = f'{R}TimingTier{RE} {B}pattern {RE}{self.pattern} | '
        m += f'{B}slots {RE}{len(self.slots)}'
        return m

    @property
    def pattern(self):
        '''The slot kinds of the whole word as one string, e.g.
        VVCCVCVC.'''
        return ''.join(slot.kind for slot in self.slots)

    def phone_to_slots(self, phone):
        '''The slots linked to a phone: two for a long vowel or
        diphthong, otherwise one.'''
        return [slot for slot in self.slots if slot.phone is phone]

    def syllable_to_slots(self, syllable):
        '''The slots of the syllable's own phones. Over all syllables
        of the word this partitions the tier.'''
        return self._phones_to_slots(syllable.phones)

    def surface_syllable_to_slots(self, syllable):
        '''The slots of the syllable's surface phones, including the
        slot of a shared ambisyllabic phone. That slot appears in the
        slot lists of both neighbouring syllables, so surface slot
        counts can sum to more than the tier length.'''
        return self._phones_to_slots(syllable.surface_phones)

    def _phones_to_slots(self, phones):
        slots = []
        for slot in self.slots:
            if slot.phone in phones: slots.append(slot)
        return slots


class Slot:
    '''One timing position on the cv tier of a word.'''

    def __init__(self, kind, phone, index):
        self.kind = kind
        self.phone = phone
        self.index = index

    def __repr__(self):
        m = f'{R}Slot{RE} {B}kind {RE}{self.kind} | '
        m += f'{B}index {RE}{self.index} | '
        m += f'{B}phone {RE}{self.phone.ipa}'
        return m

    @property
    def syllables(self):
        '''One syllable, or two for an ambisyllabic consonant slot.'''
        return self.phone.surface_syllables
