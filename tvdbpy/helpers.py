import urlparse
import xml.etree.ElementTree as ET

from functools import wraps

import requests

from tvdbpy.errors import APIKeyRequiredError, APIResponseError


def api_key_required(method):
    """Decorator to check for api_key set."""
    @wraps(method)
    def _check_api_key(self, *args, **kwargs):
        if self._api_key is None:
            raise APIKeyRequiredError("TvDB API key required.")
        result = method(self, *args, **kwargs)
        return result
    return _check_api_key


class BaseTvDB(object):
    """Base class for TvDB objects using the API."""

    _base_api_url = 'http://thetvdb.com/api/'
    _base_image_url = 'http://thetvdb.com/banners/'

    def __init__(self, client=None):
        super(BaseTvDB, self).__init__()
        self._client = client

    def _elem_value(self, xml_data, elem_name):
        elem = xml_data.find(elem_name)
        return getattr(elem, 'text', None)

    def _elem_list_value(self, xml_data, elem_name):
        value = None
        data = self._elem_value(xml_data, elem_name)
        if data:
            value = data[1:-1].split('|')
        return value

    def _get(self, path, content_type, **params):
        """Do a GET request to the given path with the specified params."""
        url = urlparse.urljoin(self._base_api_url, path)
        response = requests.get(url, params=params)

        if not response.ok:
            raise APIResponseError("Status code: %s" % response.status_code)

        # responses from tvdb are expected to be XML, utf-8 encoded
        response_content_type = response.headers.get('content-type')
        if content_type not in response_content_type:
            raise APIResponseError("Content-type: %s" % response_content_type)

        return response

    def _get_xml_data(self, path, **params):
        """Do a GET request expecting XML data."""
        response = self._get(path, 'text/xml', **params)
        xml_data = ET.fromstring(response.content)
        return xml_data
