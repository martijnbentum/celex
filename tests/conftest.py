import pytest


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    '''Keep the parse cache out of the user cache dir during tests.'''
    monkeypatch.setenv('CELEX_CACHE', str(tmp_path / 'celex_cache'))
