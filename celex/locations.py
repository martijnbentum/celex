import os
from pathlib import Path


def celex_data_path():
    '''Return the root directory holding licensed CELEX data.'''
    configured = os.environ.get('CELEX_DATA')
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).parent.parent / 'CELEX_DATA'


_pkg = Path(__file__).parent
_celex = celex_data_path()

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
