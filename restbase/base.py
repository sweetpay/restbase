"""All base classes are defined in this file."""
import logging
import os
from contextlib import contextmanager

from unittest.mock import Mock
from requests import Session


class ApiBaseException(Exception):
    def __init__(self, msg, data=None, code=None, response=None, exc=None):
        super().__init__(msg)
        self.data = data
        self.code = code
        self.response = response
        self.exc = exc

    def to_dict(self):
        return {
            "msg": self.args[0], "data": self.data, "code": self.code,
            "response": self.response, "exc": self.exc
        }


class ResponseClass:
    """The response class returning response data from API calls."""

    def __init__(self, response, code, data):
        """Init the class.

        :param response: The requests response object.
        :param code: The HTTP status code.
        :param data: The JSON decoded data.
        """
        self.response = response
        self.code = code
        self.data = data

    def __repr__(self):
        return (
            "<ResponseClass: code={0}, response={1}, data={2}>".format(
                self.code, self.response, self.data))


class BaseConnector:
    """The base class used to create API clients."""

    def __init__(self, api_token, test, timeout):
        """Initialize the checkout client used to talk to the checkout API.

        :param api_token: Same as `BaseClient`.
        :param test: Same as `BaseClient`.
        :param timeout: Same as `BaseClient`.
        """
        self.api_token = api_token
        self.test = test
        self.timeout = timeout
        self.logger = self.get_logger()

        # It is important to call this last, since the headers may
        # depend on instance attributes such as `api_token`.
        self.headers = self.create_headers()

    def create_headers(self):
        """Return headers to use in each request.

        Must be overwritten."""
        raise NotImplementedError

    def encode_data(self, method, data):
        """Encode the request data.

        Must be overwritten.

        :param method: The HTTP method for the request.
        :param data: The data to encode, if any.
        """
        raise NotImplementedError

    def decode_data(self, rawdata):
        """Decode the response returned from the server.

        This would be the place to decode JSON. Must be overwritten.

        :param rawdata: The raw data to decode.
        :return: The response data.
        """
        raise NotImplementedError

    def get_logger(self):
        """Return the logger instance to be used for logging."""
        return logging.getLogger(__name__)

    def make_request(self, url, method, params=None):
        """Make a request to a passed URL.

        :param url: The URL to send the request to.
        :param method: The method to use. Should be GET or POST.
        :param params: The parameters passed by the client.
                       Should only be used when doing a POST request
        :raise ValueError: If an incorrect `method` is passed.
        :raise TimeoutError: If a request timeout occurred.
        :raise RequestError: If an unhandled request error occurred.
        :return: Return a `ResponseClass` instance.
        """

        # We want the method to be in upper-case for comparison reasons.
        method = method.upper()

        # Set default values for the request args and kwargs.
        reqkwargs = {"timeout": self.timeout}

        # Encode the data
        reqkwargs["data"] = self.encode_data(method, params)

        # Pre process the request data.
        reqkwargs = self.pre_process_request(method, url, reqkwargs)

        # Send the actual request
        self.logger.info(
            "Sending request with method=%s to url=%s", method, url)
        resp = self.send_request(method, url, reqkwargs)

        # Try to decode the response
        data = self.decode_data(resp.text)

        # Post process the request.
        respcls = ResponseClass(resp, resp.status_code, data)
        respcls = self.post_process_request(respcls)
        return respcls

    def send_request(self, method, url, reqkwargs):
        """Send a request to the server.

        A common use-case is to raise a custom exception when the
        underlying `requests` library raises something. This could
        be accomplished by overriding this method and wrapping a try-except
        around a call to `super().send_request`. Then simply catch the
        underlying exception and raise your own.

        :param method: The HTTP method to use.
        :param url: The URL to send the request to.
        :param reqkwargs: The keyword arguments to pass to the
            request function.
        """

        # We need to create a new session on every request to
        # ensure thread-safety.
        session = self.create_session()
        # Send the actual request
        resp = session.request(method=method, url=url, **reqkwargs)
        self.logger.info(
            "Sent request to url=%s and method=%s, "
            "received status_code=%d", url, method, resp.status_code)
        return resp

    def create_session(self):
        """Return a session object to use for sending the request."""
        session = Session()
        session.headers = self.headers
        return session

    def pre_process_request(self, method, url, reqkwargs):
        """Pre process the request and return the keyword argumets for
        the request.

        This would be the place to modify headers or for modifying the data
        to send to the server (can be useful when for example authentication
        is dependent on time and thus must be calculated on every request).

        :param method: The method to use in the request. Can not be modified.
        :param url: The URL to send the request to. Can not be modified.
        :param reqkwargs: The keyword arguments to send to the
            underlying `requests` call. `data` will be present, but
            it's value and type depends on the return value of `encode_data`.
        :return: The keyword arguments to pass to the underlying
            `requests` call.
        """
        return reqkwargs

    def post_process_request(self, respcls):
        """Process the ResponseClass directly after the request was made.

        May be overwritten. Can be convenient to override when.

        :param respcls: The ResponseClass to post process.
        :return: The data returned from the server.
        """
        # Now it's time to extract the status.
        return respcls

    def __repr__(self):
        return "<{0}: test={1}>".format(type(self).__name__, self.test)


class BaseResource:
    """The base resource used to create API resources."""

    def __init__(self, test, connector, *connector_args, **connector_kwargs):
        """

        :param test: Same as `BaseClient`.
        :param connector: The connector class used to communicate with
            the API server.
        :param connector_args: The place arguments to pass to the connector.
        :param connector_kwargs: The keyword arguments to pass to
            the connector.
        """
        self.test = test
        self.client = connector(
            *connector_args, test=test, **connector_kwargs)

    @property
    def _test_url(self):
        """Return the test URL. Must be overwritten."""
        raise NotImplementedError(
            "No URL for the test server has been specified")

    @property
    def _production_url(self):
        """Return the production URL. Must be overwritten."""
        raise NotImplementedError(
            "No URL for the production server has been specified")

    @property
    def url(self):
        """Return the test or production URL, based on the current context."""
        if self.test:
            url = self._test_url
        else:
            url = self._production_url
        return url

    def _build_url(self, *args):
        """Return a URL based on the `url` and a provided path.

        :param args: The arguments which will be used to build the path.
            For example: "path" and "to" creates the path "/path/to".
        :return: A complete URL as a string.
        """
        return os.path.join(self.url, *args)

    def _api_call(self, url, method, data=None):
        """Make an API call.

        If an exception isn't raised, the operation is assumed to
        be successful.

        :param url: The URL to send the request to.
        :param method: The method on the client to use.
        :param data: The data to pass to the client method.
        :return: A `ResponseClass` instance.
        """

        # Make the actual API call.
        respcls = self.client.make_request(url, method, data)

        # The last thing we do is to check for errors. If an error
        # was found, raise an exception. If no error was found, a
        # dictionary of the response data will be returned.
        return self._check_for_errors(
            code=respcls.code, data=respcls.data, response=respcls.response)

    def _check_for_errors(self, code, data, response):
        """Inspect a response for errors.

        This method must raise relevant exceptions or return some
        sort of data to the user.

        :param code: The HTTP code returned from the server.
        :param data: The data returned from the server.
        :param response: The actual response returned from the server.
        :raise: Any exception you have defined for your library.
        :return: A dictionary representing the data from the server.
        """
        raise NotImplementedError

    def __repr__(self):
        return "<{0}>".format(type(self).__name__)


class BaseClient:
    """The interface for the API. Create an instance of this class to gain
    access to the SDK.
    """

    #: This should be a dictionary mapping a tuple of (string, version) to
    #: a `BaseResource` class. The `string` will become the attribute which can
    #: be used to contact the resource. For example, if `string=messages`,
    #: then `BaseClient().messages` will link to an initialized version of
    #: the resource. Must be overwritten.
    RESOURCE_MAPPER = {}

    #: The default connector to use. Must be overwritten.
    DEFAULT_CONNECTOR = BaseConnector

    #: The default timeout for the library.
    DEFAULT_TIMEOUT = 15

    def __init__(
            self, api_token, test, version, timeout=None, connector=None):
        """Configure the API with default values.

        :param api_token: The API token to the API.
        :param test: A boolean indicating whether to use the test
            or production environment.
        :param version: A dictionary indicating which versions of
            the API to use for different versions.
        :param timeout: Optional. The request timeout, defaults to 15.
        :param connector: Optional. The connector to use for contacting the
            API. Defaults to `self.DEFAULT_CONNECTOR`.
        """
        self.api_token = api_token
        self.test = test
        self.version = version
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.connector = connector or self.DEFAULT_CONNECTOR

        self._create_resources()

    def _create_resources(self):
        """Create the resources"""
        # Create the resources.
        for namespace, version in self.version.items():
            # Get the resource class.
            resource_cls = self._get_resource_cls(namespace, version)
            # Initialize the resource class.
            resource = resource_cls(**self._get_resource_arguments())
            # Set the resource class on the mapper.
            setattr(self, namespace, resource)

    @classmethod
    def _get_resource_cls(cls, namespace, version):
        """Retrieve the resource class with the given namespace and version.

        :param namespace: The namespace to match.
        :param version: The version to match.
        """
        try:
            return cls.RESOURCE_MAPPER[(namespace, version)]
        except KeyError:
            raise ValueError(
                "No resource with the namespace={0} and "
                "version={1}".format(namespace, version))

    def _get_resource_arguments(self):
        """Retrieve the arguments to pass to the connector."""
        return {
            "api_token": self.api_token, "test": self.test,
            "timeout": self.timeout, "connector": self.connector
        }


def _mock_manager(func):
    """Wrapper that returns a contextmanager for mocking API calls."""
    # The mock which gets set when in mocking mode.
    func._mock = None

    @contextmanager
    def manager(*args, **kwargs):
        # Setup context: Set the mock when the this context is invoked.
        func._mock = Mock(*args, **kwargs)

        # Return the mock for the context
        yield func._mock

        # Teardown context: Remove the mock
        func._mock = None

    return manager


def operation(func):
    """Decorator that should be used to mark all API operations."""
    def inner(self, *args, **kwargs):
        # Call the mock if we are in mock mode.
        if func._mock:
            # We do not include self in the call, since that will
            # make the mock's assert helpers act crazy.
            return func._mock(*args, **kwargs)
        # If we are not mocking, call the actual underlying function.
        return func(self, *args, **kwargs)

    # Create a mock manager.
    inner.mock = _mock_manager(func)

    # We set this shortcut to the function to simplify testing.
    inner._func = func
    return inner
