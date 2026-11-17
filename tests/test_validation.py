import pytest

from conftest import channel
from core.security import Problem
from core.validate import integer
from app.service import numeric


@pytest.mark.parametrize('value', ['9' * 5000, '-' + '9' * 5000])
def test_integer_rejects_oversized_strings(value):
    with pytest.raises(Problem) as error:
        integer(value, 'Wilayah', 1)
    assert error.value.status == 400


@pytest.mark.parametrize('value', [10**400, -(10**400)])
def test_numeric_rejects_integer_overflow(value):
    with pytest.raises(Problem) as error:
        numeric(value, 'Panjang meter', 0.01, 1000000)
    assert error.value.status == 400


@pytest.mark.parametrize('extra', [
    {'region_id': '9' * 5000},
    {'length': 10**400},
])
def test_channel_oversized_numbers_return_validation_error_without_saving(env, extra):
    _, clients, _ = env
    client, headers = clients['admin']
    response = client.post('/api/channels', json=channel(code='BESAR', **extra), headers=headers)
    assert response.status_code == 400
    assert len(client.get('/api/state').json()['channels']) == 2
    assert client.post('/api/channels', json=channel(code='BESAR'), headers=headers).status_code == 200


@pytest.mark.parametrize('value', [0, '0', 100, '100'])
def test_integer_accepts_range_boundaries(value):
    assert integer(value, 'Progres', 0, 100) == int(value)


@pytest.mark.parametrize('value', [0.01, '0.01', 1000000, '1000000'])
def test_numeric_accepts_range_boundaries(value):
    assert numeric(value, 'Panjang meter', 0.01, 1000000) == float(value)
