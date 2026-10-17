"""Historical fixture use must be an explicit opt-in, even beside local data."""
import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize('configuration', ['unset', 'empty', 'missing', 'before_only', 'complete'])
def test_historical_fixture_configuration_is_explicit(monkeypatch, tmp_path, configuration):
    monkeypatch.delenv('JOURNEYDELTA_CALTRAIN_ROOT', raising=False)
    if configuration == 'empty':
        monkeypatch.setenv('JOURNEYDELTA_CALTRAIN_ROOT', '')
    elif configuration not in ('unset', 'empty'):
        monkeypatch.setenv('JOURNEYDELTA_CALTRAIN_ROOT', str(tmp_path))
        if configuration in ('before_only', 'complete'):
            (tmp_path / 'caltrain-before').mkdir()
        if configuration == 'complete':
            (tmp_path / 'caltrain-after').mkdir()
    spec = importlib.util.spec_from_file_location(
        'tests._fixture_configuration_probe',
        Path(__file__).with_name('test_caltrain_integration.py'),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.DATA == (None if configuration in ('unset', 'empty') else tmp_path)
    assert module.pytestmark.args[0] is (configuration != 'complete')
