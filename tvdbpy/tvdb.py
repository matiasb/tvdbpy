from __future__ import unicode_literals

import urlparse
import xml.etree.ElementTree as ET

from datetime import datetime

import requests

from tvdbpy.errors import APIResponseError


class BaseTvDB(object):
    """Base class for TvDB objects using the API."""

    _base_api_url = 'http://thetvdb.com/api/'
    _base_image_url = 'http://thetvdb.com/banners/'

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
        if content_type != 'text/xml; charset=utf-8':
            raise APIResponseError("Content-type: %s" % content_type)

        return response


class SearchResult(BaseTvDB):
    """Series search result."""

    def __init__(self, xml_data):
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


class TvDB(BaseTvDB):
    """TvDB API client."""

    def search(self, title):
        """Search for series with the specified title."""
        response = self._get('GetSeries.php', seriesname=title)
        root = ET.fromstring(response.content)
        return [SearchResult(data) for data in root.findall('./Series')]
