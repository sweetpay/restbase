"""Test the supported mock interface."""
import pytest

from tests.utils import SomeException


class TestMocking:
    """Test the mocking feature of the library.

    Note that you should only use `client.operation` to test this,
    or you should rewrite the code. You decide.
    """

    def test_no_mock_when_not_mocking(self, client):
        assert not client.resource.create._func._mock

    def test_mock_when_mocking(self, client):
        with client.resource.create.mock() as mock:
            assert client.resource.create._func._mock is mock

    def test_mock_removed_after_mocking(self, client):
        with client.resource.create.mock():
            pass
        assert not client.resource.create._func._mock

    def test_mock_is_isolated_to_one_method(self, client):
        with client.resource.create.mock():
            assert not client.resource.other_operation._func._mock

    def test_mock_called(self, client):
        with client.resource.create.mock() as mock:
            client.resource.create(1, test=2)
        mock.assert_called_once_with(1, test=2)

    def test_kwargs_passed_to_mock(self, client):
        # Setup
        with client.resource.create.mock(
                return_value={"status": "OK"}):
            # Execute
            data = client.resource.create()
        
        # Verify
        assert data == {"status": "OK"}

    def test_with_exception(self, client):
        # Setup
        expected_exc = SomeException("Something went horribly wrong")
        with client.resource.create.mock(side_effect=expected_exc):
            # Verify: The exception should be raised.
            with pytest.raises(SomeException) as excinfo:
                # Execute
                client.resource.create(242)

        # Verify: It was the correct exception raised
        assert excinfo.value is expected_exc
