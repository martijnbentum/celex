import os
from pathlib import Path


def celex_data_path():
    '''Return the root directory holding licensed CELEX data.'''
    configured = os.environ.get('CELEX_DATA')
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).parent.parent / 'CELEX_DATA'


_pkg = Path(__file__).parent


def word_form_path(language):
    '''Return the phonology word-form file path for a language.'''
    paths = {
        'dutch':   ('DUTCH',   'DPW', 'DPW.CD'),
        'english': ('ENGLISH', 'EPW', 'EPW.CD'),
        'german':  ('GERMAN',  'GPW', 'GPW.CD'),
    }
    directory, subdirectory, filename = paths[language]
    return celex_data_path() / directory / subdirectory / filename


def lemma_path(language):
    '''Return the phonology lemma file path for a language.'''
    paths = {
        'dutch':   ('DUTCH',   'DPL', 'DPL.CD'),
        'english': ('ENGLISH', 'EPL', 'EPL.CD'),
        'german':  ('GERMAN',  'GPL', 'GPL.CD'),
    }
    directory, subdirectory, filename = paths[language]
    return celex_data_path() / directory / subdirectory / filename

# Column-name header files (hand-crafted, bundled with the package)
dutch_header   = _pkg / 'dutch_header'
english_header = _pkg / 'english_header'
german_header  = _pkg / 'german_header'
