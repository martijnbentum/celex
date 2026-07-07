from pathlib import Path

_data = Path(__file__).parent.parent / 'data'
_celex = Path(__file__).parent.parent / 'CELEX_DATA'

# Phonology word-form files (DPW / EPW / GPW)
dutch   = _celex / 'DUTCH'   / 'DPW' / 'DPW.CD'
english = _celex / 'ENGLISH' / 'EPW' / 'EPW.CD'
german  = _celex / 'GERMAN'  / 'GPW' / 'GPW.CD'

# Phonology lemma files (DPL / EPL / GPL)
dutch_lemma   = _celex / 'DUTCH'   / 'DPL' / 'DPL.CD'
english_lemma = _celex / 'ENGLISH' / 'EPL' / 'EPL.CD'
german_lemma  = _celex / 'GERMAN'  / 'GPL' / 'GPL.CD'

# Column-name header files (hand-crafted, kept in data/)
dutch_header   = _data / 'dutch_header'
english_header = _data / 'english_header'
german_header  = _data / 'german_header'
