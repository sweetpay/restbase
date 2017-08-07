import pytest

from tests.utils import SomeClient


@pytest.fixture()
def client():
    return SomeClient("api-token", test=True, version={"resource": 1})
