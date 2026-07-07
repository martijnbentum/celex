from pathlib import Path

_pkg   = Path(__file__).parent
_celex = Path(__file__).parent.parent / 'CELEX_DATA'

# Phonology word-form files (DPW / EPW / GPW)
dutch   = _celex / 'DUTCH'   / 'DPW' / 'DPW.CD'
english = _celex / 'ENGLISH' / 'EPW' / 'EPW.CD'
german  = _celex / 'GERMAN'  / 'GPW' / 'GPW.CD'

# Phonology lemma files (DPL / EPL / GPL)
dutch_lemma   = _celex / 'DUTCH'   / 'DPL' / 'DPL.CD'
english_lemma = _celex / 'ENGLISH' / 'EPL' / 'EPL.CD'
german_lemma  = _celex / 'GERMAN'  / 'GPL' / 'GPL.CD'

# Column-name header files (hand-crafted, bundled with the package)
dutch_header   = _pkg / 'dutch_header'
english_header = _pkg / 'english_header'
german_header  = _pkg / 'german_header'
