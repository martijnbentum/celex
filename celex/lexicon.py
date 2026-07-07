'''Lexicon: a loaded CELEX language file with word/syllable/phone search.'''

from collections import defaultdict

from .parser import load, load_lemmas


class Lexicon:
    '''All words from one CELEX language file, with linked lemmas and
    siblings and search methods for words, syllables and phones.'''

    def __init__(self, language_name):
        self.language = language_name
        self.words = load(language_name)
        self._link()

    @classmethod
    def _from_words(cls, words, language='test', lemmas=None):
        '''Build a Lexicon from a pre-constructed word list (for tests).
        lemmas: optional {id: Word} dict from load_lemmas(); omit to skip.
        '''
        lexicon = object.__new__(cls)
        lexicon.language = language
        lexicon.words = words
        lexicon._link(lemmas=lemmas or {})
        return lexicon

    def _link(self, lemmas=None):
        if lemmas is None:
            lemmas = load_lemmas(self.language, verbose=False)
        groups = defaultdict(list)
        for index, word in enumerate(self.words):
            word.lexicon = self
            word.index = index
            word.lemma = lemmas.get(word.id_number_lemma)
            groups[word.id_number_lemma].append(word)
        for word in self.words:
            word.siblings = [w for w in groups[word.id_number_lemma]
                if w is not word]

    def __repr__(self):
        return f'Lexicon({self.language!r}, {len(self.words)} words)'

    @property
    def syllables(self):
        '''Flat list of all syllables across all words, built on first access.'''
        if not hasattr(self, '_syllables'):
            self._syllables = [s for w in self.words for s in w.syllables]
        return self._syllables

    @property
    def phones(self):
        '''Flat list of all phones across all words, built on first access.'''
        if not hasattr(self, '_phones'):
            self._phones = [p for w in self.words for p in w.phones]
        return self._phones

    def search_words(self, word=None, ipa=None, stress_pattern=None,
                     freq_min=None, freq_max=None):
        '''Return words matching all supplied criteria.

        word:           exact orthographic match
        ipa:            phones as substring (spaces optional, e.g. "aːx" or "aː x")
        stress_pattern: exact match on syllable stress codes, e.g. "s w"
        freq_min/max:   inclusive frequency bounds
        '''
        results = self.words
        if word is not None:
            results = [w for w in results if w.word == word]
        if ipa is not None:
            query = ipa.replace(' ', '')
            results = [w for w in results
                if query in w.ipa.replace(' ', '')]
        if stress_pattern is not None:
            results = [w for w in results
                if w.stress_pattern == stress_pattern]
        if freq_min is not None:
            results = [w for w in results if w.frequency >= freq_min]
        if freq_max is not None:
            results = [w for w in results if w.frequency <= freq_max]
        return results

    def search_syllables(self, ipa=None, stress=None):
        '''Return syllables matching all supplied criteria.

        ipa:    phones as substring (spaces optional)
        stress: exact stress value: "strong", "weak" or "secondary"
        '''
        results = self.syllables
        if ipa is not None:
            query = ipa.replace(' ', '')
            results = [s for s in results if query in s.ipa.replace(' ', '')]
        if stress is not None:
            results = [s for s in results if s.stress == stress]
        return results

    def search_phones(self, ipa=None, position=None, ambisyllabic=None,
                      stressed=None):
        '''Return phones matching all supplied criteria.

        ipa:           exact ipa symbol, e.g. "p" or "aː"
        position:      syllable position: "onset", "nucleus" or "coda"
        ambisyllabic:  True / False
        stressed:      True if phone must be in a stressed syllable
        '''
        results = self.phones
        if ipa is not None:
            results = [p for p in results if p.ipa == ipa]
        if position is not None:
            results = [p for p in results if getattr(p, position)]
        if ambisyllabic is not None:
            results = [p for p in results if p.ambisyllabic == ambisyllabic]
        if stressed is not None:
            results = [p for p in results
                if p.syllable is not None and p.syllable.stressed == stressed]
        return results
