'''Small in-memory query helpers for CELEX objects.'''


class DoesNotExist(Exception):
    '''Raised when a query expected one object but found none.'''


class MultipleObjectsReturned(Exception):
    '''Raised when a query expected one object but found several.'''


LOOKUPS = {
    'contains',
    'endswith',
    'exact',
    'gt',
    'gte',
    'in',
    'isnull',
    'len',
    'lt',
    'lte',
    'startswith',
}


class QuerySet:
    '''Filter, exclude and order a fixed list of CELEX objects.'''

    def __init__(self, items, filters=None, excludes=None, ordering=None):
        self._items = list(items)
        self._filters = filters or []
        self._excludes = excludes or []
        self._ordering = ordering

    def all(self):
        '''Return a copy of this query set.'''
        return QuerySet(self._items, self._filters, self._excludes,
            self._ordering)

    def to_list(self):
        '''Materialize this query set as a list.'''
        return list(self)

    def filter(self, **kwargs):
        '''Return objects matching all lookup arguments.'''
        return QuerySet(self._items, self._filters + [kwargs],
            self._excludes, self._ordering)

    def exclude(self, **kwargs):
        '''Return objects that do not match the lookup arguments.'''
        return QuerySet(self._items, self._filters,
            self._excludes + [kwargs], self._ordering)

    def order_by(self, *fields):
        '''Return objects ordered by one or more attribute paths.'''
        return QuerySet(self._items, self._filters, self._excludes, fields)

    def get(self, **kwargs):
        '''Return exactly one object matching lookup arguments.'''
        results = self.filter(**kwargs).to_list()
        if not results:
            raise DoesNotExist(f'no object found for {kwargs}')
        if len(results) > 1:
            raise MultipleObjectsReturned(
                f'{len(results)} objects found for {kwargs}')
        return results[0]

    def get_or_none(self, **kwargs):
        '''Return one matching object, or None when none exists.'''
        try:
            return self.get(**kwargs)
        except DoesNotExist:
            return None

    def _apply(self):
        items = list(self._items)
        for kwargs in self._filters:
            items = _filter_items(items, kwargs)
        for kwargs in self._excludes:
            items = [item for item in items if not _matches_all(item, kwargs)]
        if self._ordering:
            items = sorted(items, key=lambda item: _sort_key(item,
                self._ordering))
        return items

    def __iter__(self):
        return iter(self._apply())

    def __len__(self):
        return len(self._apply())

    def __contains__(self, item):
        return item in self._apply()

    def __repr__(self):
        return f'<QuerySet n={len(self)}>'


def _filter_items(items, kwargs):
    result = []
    for item in items:
        if _matches_all(item, kwargs): result.append(item)
    return result


def _matches_all(item, kwargs):
    for lookup, expected in kwargs.items():
        if not _matches_lookup(item, lookup, expected): return False
    return True


def _matches_lookup(item, lookup, expected):
    path, lookup_name = _split_lookup(lookup)
    parts = path.split('__')
    return _matches_path(item, parts, lookup_name, expected)


def _split_lookup(lookup):
    parts = lookup.split('__')
    if parts[-1] in LOOKUPS:
        lookup_name = parts[-1]
        path = '__'.join(parts[:-1])
        if not path: raise ValueError('lookup path cannot be empty')
        return path, lookup_name
    return lookup, 'exact'


def _matches_path(value, parts, lookup_name, expected):
    if not parts:
        return _compare(value, lookup_name, expected)
    if value is None: return False
    attr = parts[0]
    rest = parts[1:]
    value = getattr(value, attr)
    if isinstance(value, list):
        if not rest:
            return _compare_list(value, lookup_name, expected)
        for item in value:
            if _matches_path(item, rest, lookup_name, expected):
                return True
        return False
    return _matches_path(value, rest, lookup_name, expected)


def _compare_list(value, lookup_name, expected):
    '''Compare a terminal list value.'''
    if lookup_name == 'exact' and not isinstance(expected, list):
        message = 'exact lookup on a list value expects a list, '
        message += f'got {type(expected).__name__}'
        raise ValueError(message)
    return _compare(value, lookup_name, expected)


def _compare(value, lookup_name, expected):
    if lookup_name == 'exact': return value == expected
    if lookup_name == 'contains':
        if value is None: return False
        return expected in value
    if lookup_name == 'startswith':
        if value is None: return False
        return value.startswith(expected)
    if lookup_name == 'endswith':
        if value is None: return False
        return value.endswith(expected)
    if lookup_name == 'in': return value in expected
    if lookup_name == 'isnull':
        if not isinstance(expected, bool):
            raise ValueError('__isnull lookup expects a boolean')
        return (value is None) == expected
    if lookup_name == 'len':
        if not isinstance(expected, int):
            raise ValueError('__len lookup expects an integer')
        return len(value) == expected
    if value is None: return False
    if lookup_name == 'gt': return value > expected
    if lookup_name == 'gte': return value >= expected
    if lookup_name == 'lt': return value < expected
    if lookup_name == 'lte': return value <= expected
    raise ValueError(f'unknown lookup {lookup_name!r}')


def _sort_key(item, ordering):
    keys = []
    for field in ordering:
        if field.startswith('-'):
            value = _resolve_path(item, field[1:])
            keys.append(_Descending((value is not None, value)))
        else:
            value = _resolve_path(item, field)
            keys.append((value is not None, value))
    return tuple(keys)


def _resolve_path(item, path):
    '''Follow an attribute path; a None link resolves to None.'''
    value = item
    for attr in path.split('__'):
        if value is None: break
        value = getattr(value, attr)
    return value


class _Descending:
    '''Reverse-sort wrapper.'''

    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        return self.value > other.value

    def __eq__(self, other):
        return self.value == other.value
