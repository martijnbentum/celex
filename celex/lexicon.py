'''Lexicon: a loaded CELEX language file with word/syllable/phone search.'''

import warnings
from collections import defaultdict

from .parser import load, load_lemmas
from .query import QuerySet


_LOAD_LEMMAS = object()
_PHONE_POSITIONS = {'coda', 'nucleus', 'onset'}


def _validate_phone_position(position):
    if position is None or position in _PHONE_POSITIONS:
        return
    valid = "', '".join(sorted(_PHONE_POSITIONS))
    raise ValueError(f"unknown phone position {position!r}, expected '{valid}'")


class Lexicon:
    '''All words from one CELEX language file, with linked lemmas and
    siblings and search methods for words, syllables and phones.'''

    def __init__(self, language_name, use_cache=True):
        self.language = language_name
        self._use_cache = use_cache
        self._bad_celex_lines = []
        self.words = load(language_name, bad_lines=self._bad_celex_lines,
            use_cache=use_cache)
        self._link_words()
        self._link_siblings()
        self._link_lemmas()

    @classmethod
    def _from_words(cls, words, language='test', lemmas=None):
        '''Build a Lexicon from a pre-constructed word list (for tests).
        lemmas: optional {id: Word} dict from load_lemmas(); omit to skip.
        '''
        lexicon = object.__new__(cls)
        lexicon.language = language
        lexicon._use_cache = False
        lexicon._bad_celex_lines = []
        lexicon.words = words
        lexicon._link_words()
        lexicon._link_siblings()
        lexicon._link_lemmas(lemmas=lemmas or {})
        return lexicon

    def _link_words(self):
        '''Attach each word to this lexicon and assign file-order indices.'''
        for index, word in enumerate(self.words):
            word.lexicon = self
            word.index = index

    def _link_siblings(self):
        '''Link words sharing a positive lemma id.'''
        groups = defaultdict(list)
        for word in self.words:
            if word.id_number_lemma and word.id_number_lemma > 0:
                groups[word.id_number_lemma].append(word)
        for word in self.words:
            if not word.id_number_lemma or word.id_number_lemma <= 0:
                word.siblings = []
                continue
            word.siblings = [w for w in groups[word.id_number_lemma]
                if w is not word]

    def _link_lemmas(self, lemmas=_LOAD_LEMMAS):
        '''Attach lemma Word objects when lemma files are available.'''
        if lemmas is _LOAD_LEMMAS:
            try:
                lemmas = load_lemmas(self.language, verbose=False,
                    use_cache=self._use_cache)
            except FileNotFoundError as error:
                m = str(error)
                m += '\n\nLemma files are optional for Lexicon loading; '
                m += 'word.lemma and word.family will be None.'
                warnings.warn(m, RuntimeWarning, stacklevel=2)
                lemmas = {}
        for word in self.words:
            word.lemma = lemmas.get(word.id_number_lemma)

    def __repr__(self):
        return f'Lexicon({self.language!r}, {len(self.words)} words)'

    @property
    def bad_celex_lines(self):
        '''Rows skipped while parsing the word-form file.'''
        return list(self._bad_celex_lines)

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

    @property
    def word_index(self):
        '''Dict mapping orthography to its words in file order,
        built on first access.'''
        if not hasattr(self, '_word_index'):
            index = defaultdict(list)
            for word in self.words:
                index[word.word].append(word)
            self._word_index = dict(index)
        return self._word_index

    @property
    def words_query(self):
        '''Query root for words in this lexicon.'''
        return QuerySet(self.words)

    @property
    def syllables_query(self):
        '''Query root for syllables in this lexicon.'''
        return QuerySet(self.syllables)

    @property
    def phones_query(self):
        '''Query root for phones in this lexicon.'''
        return QuerySet(self.phones)

    def search_words(self, word=None, ipa=None, stress_pattern=None,
                     freq_min=None, freq_max=None):
        '''Return words matching all supplied criteria.

        word:           exact orthographic match
        ipa:            phones as substring (spaces optional, e.g. "aːx" or "aː x")
        stress_pattern: exact match on syllable stress codes, e.g. "s w"
        freq_min/max:   inclusive frequency bounds
        '''
        if word is not None:
            results = list(self.word_index.get(word, []))
        else:
            results = self.words
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
        _validate_phone_position(position)
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
