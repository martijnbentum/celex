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
        results = []
        for word in self.words:
            for syllable in word.syllables:
                if ipa is not None:
                    query = ipa.replace(' ', '')
                    if query not in syllable.ipa.replace(' ', ''):
                        continue
                if stress is not None and syllable.stress != stress:
                    continue
                results.append(syllable)
        return results

    def search_phones(self, ipa=None, position=None, ambisyllabic=None,
                      stressed=None):
        '''Return phones matching all supplied criteria.

        ipa:           exact ipa symbol, e.g. "p" or "aː"
        position:      syllable position: "onset", "nucleus" or "coda"
        ambisyllabic:  True / False
        stressed:      True if phone must be in a stressed syllable
        '''
        results = []
        for word in self.words:
            for phone in word.phones:
                if ipa is not None and phone.ipa != ipa:
                    continue
                if position is not None:
                    if position == 'onset' and not phone.onset:
                        continue
                    elif position == 'nucleus' and not phone.nucleus:
                        continue
                    elif position == 'coda' and not phone.coda:
                        continue
                if ambisyllabic is not None \
                        and phone.ambisyllabic != ambisyllabic:
                    continue
                if stressed is not None:
                    in_stressed = (phone.syllable is not None
                        and phone.syllable.stressed)
                    if in_stressed != stressed:
                        continue
                results.append(phone)
        return results
