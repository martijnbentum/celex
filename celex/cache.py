'''On-disk cache for parsed CELEX files.

load() spends ~14s aligning the celex column of a full language
file; the result only changes when the data file or the parser
changes. Parse results are pickled to ~/.cache/celex (override
with CELEX_CACHE), keyed on the data file's mtime and size plus
cache_version. Each name maps to one fixed file that is overwritten
in place on rewrite, so stale caches never accumulate. Bump
cache_version whenever the parse result or the shape of the pickled
objects changes; see AGENTS.md for examples.
'''

import pickle

from . import locations

cache_version = 1


def _stamp(data_path):
    status = data_path.stat()
    return (cache_version, status.st_mtime_ns, status.st_size)


def _cache_file(name):
    return locations.cache_dir() / f'{name}.pickle'


def read(name, data_path):
    '''The cached payload for name, or None when stale or absent.'''
    path = _cache_file(name)
    if not path.exists() or not data_path.exists(): return None
    try:
        with open(path, 'rb') as fin:
            entry = pickle.load(fin)
    except (pickle.UnpicklingError, EOFError, AttributeError, OSError):
        return None
    if entry.get('stamp') != _stamp(data_path): return None
    return entry.get('payload')


def write(name, data_path, payload):
    '''Pickle payload for name, overwriting any previous cache file.'''
    path = _cache_file(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {'stamp': _stamp(data_path), 'payload': payload}
    with open(path, 'wb') as fout:
        pickle.dump(entry, fout, protocol=pickle.HIGHEST_PROTOCOL)
