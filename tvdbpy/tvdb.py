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
from tvdbpy.helpers import BaseTvDB, api_key_required


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
    """Series details."""

    def __init__(self, xml_data, client=None):
        super(Series, self).__init__(xml_data, client=client)
        self.runtime = self._elem_value(xml_data, 'Runtime')
        self.status = self._elem_value(xml_data, 'Status')
        self._poster = self._elem_value(xml_data, 'poster')
        self.actors = self._elem_list_value(xml_data, 'Actors')
        self.genre = self._elem_list_value(xml_data, 'Genre')

    @property
    def poster(self):
        return urlparse.urljoin(self._base_image_url, self._poster)


class Episode(BaseTvDB):
    """Episode details."""

    def __init__(self, xml_data, client=None):
        super(Episode, self).__init__(client=client)
        self.id = self._elem_value(xml_data, 'id')
        self.imdb_id = self._elem_value(xml_data, 'IMDB_ID')
        self.series_id = self._elem_value(xml_data, 'seriesid')
        self.number = self._elem_value(xml_data, 'EpisodeNumber')
        self.season = self._elem_value(xml_data, 'SeasonNumber')
        self.name = self._elem_value(xml_data, 'EpisodeName')
        self.overview = self._elem_value(xml_data, 'Overview')
        self.guest_stars = self._elem_list_value(xml_data, 'GuestStars')
        self.director = self._elem_value(xml_data, 'Director')
        self.writer = self._elem_value(xml_data, 'Writer')
        self.language = self._elem_value(xml_data, 'Language')
        self._image = self._elem_value(xml_data, 'filename')
        self._first_aired = self._elem_value(xml_data, 'FirstAired')

    def __str__(self):
        return "Episode: %s" % self.name

    @property
    def first_aired(self):
        res = None
        if self._first_aired is not None:
            res = datetime.strptime(self._first_aired, "%Y-%m-%d").date()
        return res

    @property
    def image(self):
        return urlparse.urljoin(self._base_image_url, self._image)


class TvDB(BaseTvDB):
    """TvDB API client."""

    def __init__(self, api_key=None):
        super(TvDB, self).__init__(client=None)
        self._api_key = api_key

    def _parse_response(self, response, cls, key, multiple=False):
        """Parse XML response and return expected cls instance(s)."""
        result = None
        root = ET.fromstring(response.content)
        if multiple:
            data = root.findall(key)
            if data is not None:
                result = [cls(d, client=self) for d in data]
        else:
            data = root.find(key)
            if data is not None:
                result = cls(data, client=self)
        return result

    def search(self, title):
        """Search for series with the specified title."""
        response = self._get('GetSeries.php', seriesname=title)
        return self._parse_response(
            response, SearchResult, './Series', multiple=True)

    @api_key_required
    def get_series_by_id(self, series_id):
        """Get Series detail by series id."""
        path = '%s/series/%s/en.xml' % (self._api_key, series_id)
        response = self._get(path)
        return self._parse_response(response, Series, './Series')

    @api_key_required
    def get_episode_by_id(self, episode_id):
        """Get Episode details by episode id."""
        path = '%s/episodes/%s/en.xml' % (self._api_key, episode_id)
        response = self._get(path)
        return self._parse_response(response, Episode, './Episode')

    @api_key_required
    def get_episode(self, series_id, season, number):
        """Get Episode details by season/number."""
        path = '%s/series/%s/default/%s/%s/en.xml' % (
            self._api_key, series_id, season, number)
        response = self._get(path)
        return self._parse_response(response, Episode, './Episode')
