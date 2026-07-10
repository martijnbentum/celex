'''Lexicon: a loaded CELEX language file with query roots.'''

import warnings
from collections import defaultdict

from .parser import load, load_lemmas
from .query import QuerySet


_LOAD_LEMMAS = object()


class LexiconQuery:
    '''Query roots for words, syllables and phones in one lexicon.'''

    def __init__(self, lexicon):
        self.lexicon = lexicon

    @property
    def words(self):
        '''Query words in this lexicon. Exact lookups on label and
        word are index-accelerated (built lazily on first use).'''
        if not hasattr(self, '_words'):
            self._words = QuerySet(self.lexicon.words,
                index_fields=('label', 'word'))
        return self._words

    @property
    def syllables(self):
        '''Query syllables in this lexicon.'''
        if not hasattr(self, '_syllables'):
            self._syllables = QuerySet(self.lexicon.syllables)
        return self._syllables

    @property
    def phones(self):
        '''Query phones in this lexicon.'''
        if not hasattr(self, '_phones'):
            self._phones = QuerySet(self.lexicon.phones)
        return self._phones


class Lexicon:
    '''All words from one CELEX language file, with linked lemmas and
    siblings and query roots for words, syllables and phones.'''

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
    def query(self):
        '''Query namespace for words, syllables and phones.'''
        if not hasattr(self, '_query'):
            self._query = LexiconQuery(self)
        return self._query
