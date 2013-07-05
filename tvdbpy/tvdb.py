import urlparse
import xml.etree.ElementTree as ET

import requests

from tvdbpy.errors import APIResponseError


class BaseTvDB(object):
    """Base class for TvDB objects using the API."""

    base_api_url = 'http://thetvdb.com/api/'

    def _get(self, path, **params):
        """Do a GET request to the given path with the specified params."""
        url = urlparse.urljoin(self.base_api_url, path)
        response = requests.get(url, params=params)

        if not response.ok:
            raise APIResponseError("Status code: %s" % response.status_code)

        # responses from tvdb are expected to be XML, utf-8 encoded
        content_type = response.headers.get('content-type')
        if content_type != 'text/xml; charset=utf-8':
            raise APIResponseError("Content-type: %s" % content_type)

        return response


class TvDB(BaseTvDB):
    """TvDB API client."""

    def search(self, title):
        """Search for series with the specified title."""
        response = self._get('GetSeries.php', seriesname=title)
        root = ET.fromstring(response.text)
        return root.findall('./Series')
