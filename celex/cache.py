'''On-disk cache for parsed CELEX files.

load() spends ~14s aligning the celex column of a full language
file; the result only changes when the data file or the parser
changes. Parse results are pickled to ~/.cache/celex (override
with CELEX_CACHE), keyed on the data file's mtime and size plus
cache_version. Each name maps to one fixed file that is atomically
replaced on rewrite, so stale caches never accumulate. Bump
cache_version whenever the parse result or the shape of the pickled
objects changes; see AGENTS.md for examples.
'''

import os
import pickle
import tempfile

from . import locations

cache_version = 3


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
    '''Pickle payload for name, atomically replacing any previous
    cache file: written to a temp file in the cache directory first,
    then renamed, so a reader never sees a partial write and an
    interrupted write leaves the previous cache intact.'''
    path = _cache_file(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {'stamp': _stamp(data_path), 'payload': payload}
    handle, temporary = tempfile.mkstemp(dir=path.parent,
        prefix=f'{name}-', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as fout:
            pickle.dump(entry, fout, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(temporary, path)
    except BaseException:
        try: os.unlink(temporary)
        except OSError: pass
        raise
