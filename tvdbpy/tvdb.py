from __future__ import unicode_literals

import urlparse
import xml.etree.ElementTree as ET

from datetime import datetime

import requests

from tvdbpy.errors import (
    APIClientNotAvailableError,
    APIKeyRequiredError,
    APIResponseError,
)


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

    def _get(self, path, **params):
        """Do a GET request to the given path with the specified params."""
        url = urlparse.urljoin(self._base_api_url, path)
        response = requests.get(url, params=params)

        if not response.ok:
            raise APIResponseError("Status code: %s" % response.status_code)

        # responses from tvdb are expected to be XML, utf-8 encoded
        content_type = response.headers.get('content-type')
        if 'text/xml' not in content_type:
            raise APIResponseError("Content-type: %s" % content_type)

        return response


class BaseSeries(BaseTvDB):
    """Minimum shared details for Series and SearchResult."""

    def __init__(self, xml_data, client=None):
        super(BaseSeries, self).__init__(client=client)
        self.id = self._elem_value(xml_data, 'id')
        self.imdb_id = self._elem_value(xml_data, 'IMDB_ID')
        self.name = self._elem_value(xml_data, 'SeriesName')
        self.overview = self._elem_value(xml_data, 'Overview')
        self.language = self._elem_value(xml_data, 'language')
        self._first_aired = self._elem_value(xml_data, 'FirstAired')
        self.network = self._elem_value(xml_data, 'Network')
        self._banner = self._elem_value(xml_data, 'banner')

    def __str__(self):
        return "Series: %s" % self.name

    @property
    def banner(self):
        return urlparse.urljoin(self._base_image_url, self._banner)

    @property
    def first_aired(self):
        res = None
        if self._first_aired is not None:
            res = datetime.strptime(self._first_aired, "%Y-%m-%d").date()
        return res


class SearchResult(BaseSeries):
    """Series search result."""

    def get_series(self):
        if self._client is None:
            raise APIClientNotAvailableError("Missing TvDB client")
        return self._client.get_series_by_id(self.id)


class Series(BaseSeries):

    def __init__(self, xml_data, client=None):
        super(Series, self).__init__(xml_data, client=client)
        self.runtime = self._elem_value(xml_data, 'Runtime')
        self.status = self._elem_value(xml_data, 'Status')
        self._poster = self._elem_value(xml_data, 'poster')
        self.genre = []
        genre_data = self._elem_value(xml_data, 'Genre')
        if genre_data:
            self.genre = genre_data[1:-1].split('|')

    @property
    def poster(self):
        return urlparse.urljoin(self._base_image_url, self._poster)


class TvDB(BaseTvDB):
    """TvDB API client."""

    def __init__(self, api_key=None):
        super(TvDB, self).__init__(client=None)
        self._api_key = api_key

    def search(self, title):
        """Search for series with the specified title."""
        response = self._get('GetSeries.php', seriesname=title)
        root = ET.fromstring(response.content)
        results = root.findall('./Series')
        return [SearchResult(data, client=self) for data in results]

    def get_series_by_id(self, series_id):
        """Get Series detail by series id."""
        series = None
        if self._api_key is None:
            raise APIKeyRequiredError("TvDB API key required.")

        path = '%s/series/%s/en.xml' % (self._api_key, series_id)
        response = self._get(path)
        root = ET.fromstring(response.content)
        result = root.find('./Series')
        if result is not None:
            series = Series(result, client=self)
        return series
