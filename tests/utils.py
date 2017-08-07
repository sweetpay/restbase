import json

from restbase.base import ApiBaseException, BaseConnector, BaseResource, \
    BaseClient, operation


class SomeException(ApiBaseException):
    pass


class SomeConnector(BaseConnector):

    def create_headers(self):
        return {
            "Authorization": self.api_token, "User-Agent": "Python SDK",
            "Content-Type": "application/json", "Accept": "application/json"
        }

    def encode_data(self, method, data):
        return json.dumps(data)

    def decode_data(self, rawdata):
        return json.loads(rawdata)


class SomeResource(BaseResource):

    production_url = "https://example.com"
    test_url = "https://test.example.com"

    def _check_for_errors(self, code, data, response):
        if code != 200:
            raise SomeException(
                "The API request was unsuccessful", data=data, code=code,
                response=response)
        return data

    @operation
    def create(self, **data):
        url = self._build_url("some", "path")
        return self._api_call(url, "POST", data)

    @operation
    def other_operation(self, id):
        url = self._build_url("other", str(id), "path")
        return self._api_call(url, "GET")


class SomeClient(BaseClient):
    RESOURCE_MAPPER = {
        ("resource", 1): SomeResource
    }

    DEFAULT_CONNECTOR = SomeConnector
