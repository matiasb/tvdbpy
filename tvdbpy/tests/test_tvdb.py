import codecs
import os
import unittest
import xml.etree.ElementTree as ET

from datetime import date
from io import BytesIO

import mock
import requests

from tvdbpy import TvDB
from tvdbpy.errors import (
    APIClientNotAvailableError,
    APIKeyRequiredError,
    APIResponseError,
)
from tvdbpy.tvdb import Episode, SearchResult, Series


TESTS_DIR = os.path.dirname(os.path.realpath(__file__))


class RequestsBytesIO(BytesIO):
    """BytesIO expected by requests."""

    def read(self, chunk_size, *args, **kwargs):
        return super(RequestsBytesIO, self).read(chunk_size)


class BaseTestCase(unittest.TestCase):
    """Base test case."""

    def setUp(self):
        patcher = mock.patch('tvdbpy.tvdb.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)

    def response(self, method='GET', status_code=200, filename=None,
                 content_type='text/xml'):
        """Set a custom response from a file."""
        data = ''
        if filename is not None:
            path = os.path.join(TESTS_DIR, 'xml', filename)
            with codecs.open(path, 'r', 'utf-8') as xml:
                data = xml.read()

        response = requests.Response()
        response.status_code = status_code
        response.headers['content-type'] = content_type
        response.encoding = 'utf-8'
        response.raw = RequestsBytesIO(data.encode('utf-8'))

        requests_method = getattr(self.requests, method.lower())
        setattr(requests_method, 'return_value', response)


class BaseSeriesMixin(object):
    """Shared tests between SearchResult and Series."""

    def test_base_attrs(self):
        expected = ['id', 'imdb_id', 'name', 'overview', 'language',
                    'first_aired', 'network', 'banner']
        for attr in expected:
            unexpected = object()
            value = getattr(self.result, attr, unexpected)
            self.assertNotEqual(value, unexpected)

    def test_base_values(self):
        self.assertEqual(self.result.id, '80348')
        self.assertEqual(self.result.name, 'Chuck')
        self.assertEqual(self.result.first_aired, date(2007, 9, 24))
        self.assertEqual(
            self.result.banner,
            'http://thetvdb.com/banners/graphical/80348-g32.jpg')

    def test_client_set(self):
        self.assertIsNotNone(self.result._client)


class TvDBSearchResultTestCase(BaseTestCase, BaseSeriesMixin):
    """Test search result instance."""

    def setUp(self):
        super(TvDBSearchResultTestCase, self).setUp()
        self.response(filename='getseries.xml')
        tvdb = TvDB(api_key='123456789')
        results = tvdb.search('chuck')
        self.result = results[0]

    def test_search_result_from_xml(self):
        xml = """
            <Series>
                <id>80348</id>
                <SeriesName>Chuck</SeriesName>
                <banner>graphical/80348-g32.jpg</banner>
                <Overview>description</Overview>
                <FirstAired>2007-09-24</FirstAired>
                <IMDB_ID>tt0934814</IMDB_ID>
            </Series>"""
        result = SearchResult(ET.fromstring(xml))
        self.assertEqual(result.id, '80348')
        self.assertEqual(result.name, 'Chuck')
        # when not available, field is None
        self.assertIsNone(result.network)
        # client is not set since result was not generated from search
        self.assertIsNone(result._client)

    def test_is_search_result(self):
        self.assertIsInstance(self.result, SearchResult)

    def test_from_xml_get_series(self):
        xml = """
            <Series>
                <id>80348</id>
                <SeriesName>Chuck</SeriesName>
                <banner>graphical/80348-g32.jpg</banner>
                <Overview>description</Overview>
                <FirstAired>2007-09-24</FirstAired>
                <IMDB_ID>tt0934814</IMDB_ID>
            </Series>"""
        result = SearchResult(ET.fromstring(xml))
        self.assertRaises(APIClientNotAvailableError, result.get_series)

    def test_get_series(self):
        self.response(filename='series.xml')
        result = self.result.get_series()

        self.assertIsInstance(result, Series)
        self.requests.get.assert_called_with(
            'http://thetvdb.com/api/123456789/series/80348/en.xml', params={})


class TvDBSeriesTestCase(BaseTestCase, BaseSeriesMixin):
    """TvDB Series test case."""

    def setUp(self):
        super(TvDBSeriesTestCase, self).setUp()
        self.response(filename='series.xml')
        tvdb = TvDB(api_key='123456789')
        self.result = tvdb.get_series_by_id('80348')

    def test_series_from_xml(self):
        xml = """
            <Series>
                <id>80348</id>
                <SeriesName>Chuck</SeriesName>
                <banner>graphical/80348-g32.jpg</banner>
                <poster>graphical/80348.jpg</poster>
                <Overview>description</Overview>
                <FirstAired>2007-09-24</FirstAired>
                <IMDB_ID>tt0934814</IMDB_ID>
            </Series>"""
        result = Series(ET.fromstring(xml))
        self.assertEqual(result.id, '80348')
        self.assertEqual(result.name, 'Chuck')
        self.assertEqual(
            result.poster,
            'http://thetvdb.com/banners/graphical/80348.jpg')
        # when not available, field is None
        self.assertIsNone(result.network)
        # client is not set since result was not generated from search
        self.assertIsNone(result._client)

    def test_is_series(self):
        self.assertIsInstance(self.result, Series)

    def test_extra_values(self):
        self.assertEqual(self.result.status, 'Ended')
        self.assertEqual(self.result.runtime, '60')
        self.assertEqual(
            self.result.actors,
            ['Zachary Levi', 'Yvonne Strahovski', 'Joshua Gomez',
             'Adam Baldwin'])
        self.assertEqual(
            self.result.genre, ['Action', 'Adventure', 'Comedy', 'Drama'])


class TvDBEpisodeTestCase(BaseTestCase):
    """Test episode instance."""

    def setUp(self):
        super(TvDBEpisodeTestCase, self).setUp()
        self.response(filename='episode.xml')
        tvdb = TvDB(api_key='123456789')
        self.result = tvdb.get_episode_by_id(332179)

    def test_episode_attrs(self):
        expected = ['id', 'imdb_id', 'name', 'overview', 'language',
                    'first_aired', 'series_id', 'number', 'season', 'image',
                    'guest_stars', 'director', 'writer']
        for attr in expected:
            unexpected = object()
            value = getattr(self.result, attr, unexpected)
            self.assertNotEqual(value, unexpected)

    def test_base_values(self):
        self.assertEqual(self.result.id, '332179')
        self.assertEqual(self.result.name, 'Chuck Versus the Intersect')
        self.assertEqual(self.result.first_aired, date(2007, 9, 24))
        self.assertEqual(
            self.result.image,
            'http://thetvdb.com/banners/episodes/80348/332179.jpg')

    def test_client_set(self):
        self.assertIsNotNone(self.result._client)

    def test_result_from_xml(self):
        xml = """
            <Episode>
                <id>332179</id>
                <EpisodeName>Testing</EpisodeName>
                <Overview>description</Overview>
                <FirstAired>2007-09-24</FirstAired>
                <IMDB_ID>tt0934814</IMDB_ID>
            </Episode>"""
        result = Episode(ET.fromstring(xml))
        self.assertEqual(result.id, '332179')
        self.assertEqual(result.name, 'Testing')
        # when not available, field is None
        self.assertIsNone(result.season)
        # client is not set since result was not generated from API client
        self.assertIsNone(result._client)

    def test_is_episode(self):
        self.assertIsInstance(self.result, Episode)


class AnonymousTvDBTestCase(BaseTestCase):
    """TvDB client without API key test case."""

    def setUp(self):
        super(AnonymousTvDBTestCase, self).setUp()
        self.tvdb = TvDB()

    def test_response_error(self):
        self.response(status_code=404)

        with self.assertRaises(APIResponseError):
            results = self.tvdb.search('something')

    def test_response_unexpected_content_type(self):
        self.response(status_code=200, content_type='text/plain')

        with self.assertRaises(APIResponseError):
            results = self.tvdb.search('something')

    def test_search_no_results(self):
        self.response(filename='empty.xml')
        results = self.tvdb.search('nothing')

        self.assertEqual(results, [])
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/GetSeries.php',
            params={'seriesname': 'nothing'})

    def test_search_results(self):
        self.response(filename='getseries.xml')
        results = self.tvdb.search('chuck')

        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/GetSeries.php',
            params={'seriesname': 'chuck'})
        self.assertEqual(len(results), 7)

    def test_get_series_by_id_requires_api_key(self):
        with self.assertRaises(APIKeyRequiredError):
            self.tvdb.get_series_by_id(1111)

    def test_get_episode_by_id_requires_api_key(self):
        with self.assertRaises(APIKeyRequiredError):
            self.tvdb.get_episode_by_id(1111)


class TvDBTestCase(BaseTestCase):
    """TvDB client with API key test case."""

    def setUp(self):
        super(TvDBTestCase, self).setUp()
        self.tvdb = TvDB(api_key='123456789')

    def test_get_series_by_id(self):
        self.response(filename='series.xml')
        result = self.tvdb.get_series_by_id(321)

        self.assertIsInstance(result, Series)
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/series/321/en.xml', params={})

    def test_get_series_by_id_missing_data(self):
        self.response(filename='empty.xml')
        result = self.tvdb.get_series_by_id(321)

        self.assertIsNone(result)
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/series/321/en.xml', params={})

    def test_get_episode_by_id(self):
        self.response(filename='episode.xml')
        result = self.tvdb.get_episode_by_id(332179)

        self.assertIsInstance(result, Episode)
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/episodes/332179/en.xml',
            params={})

    def test_get_episode_by_id_missing_data(self):
        self.response(filename='empty.xml')
        result = self.tvdb.get_episode_by_id(321)

        self.assertIsNone(result)
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/episodes/321/en.xml', params={})
