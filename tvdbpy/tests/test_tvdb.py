import codecs
import os
import unittest
import xml.etree.ElementTree as ET

from datetime import date, datetime
from io import BytesIO

import mock
import requests

from tvdbpy import TvDB
from tvdbpy.errors import (
    APIClientNotAvailableError,
    APIKeyRequiredError,
    APIResponseError,
    TvDBException,
)
from tvdbpy.tvdb import Episode, SearchResult, Series, Update


TESTS_DIR = os.path.dirname(os.path.realpath(__file__))


class RequestsBytesIO(BytesIO):
    """BytesIO expected by requests."""

    def read(self, chunk_size, *args, **kwargs):
        return super(RequestsBytesIO, self).read(chunk_size)


class BaseTestCase(unittest.TestCase):
    """Base test case."""

    def setUp(self):
        patcher = mock.patch('tvdbpy.helpers.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)

    def response(self, method='GET', status_code=200, filename=None,
                 content_type='text/xml'):
        """Set a custom response from a file."""
        data = ''
        if filename is not None:
            path = os.path.join(TESTS_DIR, 'testdata', filename)
            if content_type.startswith('text/'):
                with codecs.open(path, 'r', 'utf-8') as f:
                    data = f.read()
                    data = data.encode('utf-8')
            else:
                with open(path, 'rb') as f:
                    data = f.read()

        response = requests.Response()
        response.status_code = status_code
        response.headers['content-type'] = content_type
        response.encoding = 'utf-8'
        response.raw = RequestsBytesIO(data)

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
                <EpisodeNumber>1</EpisodeNumber>
                <SeasonNumber>2</SeasonNumber>
                <Overview>description</Overview>
                <FirstAired>2007-09-24</FirstAired>
                <IMDB_ID>tt0934814</IMDB_ID>
            </Episode>"""
        result = Episode(ET.fromstring(xml))
        self.assertEqual(result.id, '332179')
        self.assertEqual(result.name, 'Testing')
        # when not available, field is None
        self.assertEqual(result.number, 1)
        self.assertEqual(result.season, 2)
        # client is not set since result was not generated from API client
        self.assertIsNone(result._client)

    def test_is_episode(self):
        self.assertIsInstance(self.result, Episode)

    def test_get_series(self):
        self.response(filename='series.xml')
        result = self.result.series

        self.assertIsInstance(result, Series)
        self.requests.get.assert_called_with(
            'http://thetvdb.com/api/123456789/series/80348/en.xml', params={})


class TvDBUpdatesTestCase(BaseTestCase):
    """Test updates instance."""

    def setUp(self):
        super(TvDBUpdatesTestCase, self).setUp()
        self.response(
            filename='updates_day.zip', content_type='application/zip')
        self.tvdb = TvDB(api_key='123456789')
        self.results = self.tvdb.updated()

    def test_client_set(self):
        result = self.results[0]
        self.assertIsNotNone(result._client)

    def test_update_attrs(self):
        result = self.results[0]
        expected = ['id', 'kind', 'series', 'season', 'path',
                    'type', 'format', 'language', 'timestamp']
        for attr in expected:
            unexpected = object()
            value = getattr(result, attr, unexpected)
            self.assertNotEqual(value, unexpected)

    def test_id_only_update_attrs(self):
        self.response(filename='updates_since.xml')
        results = self.tvdb.updated_since(1234567890)

        result = results[0]
        expected = ['id', 'kind']
        for attr in expected:
            unexpected = object()
            value = getattr(result, attr, unexpected)
            self.assertNotEqual(value, unexpected)

        unexpected = ['series', 'season', 'path', 'type', 'format', 'language',
                      'timestamp']
        for attr in unexpected:
            unexpected = object()
            value = getattr(result, attr, unexpected)
            self.assertEqual(value, unexpected)

    def test_id_only_updates(self):
        self.response(filename='updates_since.xml')
        results = self.tvdb.updated_since(1234567890)

        series = results[0]
        episode = results[1]

        self.assertEqual(series.id, '80348')
        self.assertEqual(series.kind, TvDB.SERIES)
        self.assertEqual(episode.id, '332179')
        self.assertEqual(episode.kind, TvDB.EPISODE)

    def test_series_update_values(self):
        result = self.results[0]
        assert result.kind == TvDB.SERIES

        self.assertEqual(result.id, '80348')
        self.assertEqual(result.timestamp, datetime(2009, 2, 13, 23, 31, 30))
        self.assertEqual(result.series, None)

    def test_get_series_item(self):
        result = self.results[0]
        assert result.kind == TvDB.SERIES

        patcher = mock.patch.object(self.tvdb, 'get_series_by_id')
        mock_get = patcher.start()
        self.addCleanup(patcher.stop)

        result.get_updated_item()
        mock_get.assert_called_once_with('80348')

    def test_episode_update_values(self):
        result = self.results[1]
        assert result.kind == TvDB.EPISODE

        self.assertEqual(result.id, '332179')
        self.assertEqual(result.series, '80348')
        self.assertEqual(result.timestamp, datetime(2009, 2, 13, 23, 31, 30))

    def test_get_episode_item(self):
        result = self.results[1]
        assert result.kind == TvDB.EPISODE

        patcher = mock.patch.object(self.tvdb, 'get_episode_by_id')
        mock_get = patcher.start()
        self.addCleanup(patcher.stop)

        result.get_updated_item()
        mock_get.assert_called_once_with('332179')

    def test_banner_update_values(self):
        result = self.results[2]
        assert result.kind == TvDB.BANNER

        self.assertEqual(result.id, None)
        self.assertEqual(result.series, '80348')
        self.assertEqual(result.timestamp, datetime(2009, 2, 13, 23, 31, 30))
        self.assertEqual(result.path, 'posters/77170.jpg')

    def test_get_banner_item(self):
        result = self.results[2]
        assert result.kind == TvDB.BANNER

        item = result.get_updated_item()
        self.assertEqual(item, 'http://thetvdb.com/banners/posters/77170.jpg')


class AnonymousTvDBTestCase(BaseTestCase):
    """TvDB client without API key test case."""

    def setUp(self):
        super(AnonymousTvDBTestCase, self).setUp()
        self.tvdb = TvDB()

    def test_response_error(self):
        self.response(status_code=404)

        with self.assertRaises(APIResponseError):
            self.tvdb.search('something')

    def test_response_unexpected_content_type(self):
        self.response(status_code=200, content_type='text/plain')

        with self.assertRaises(APIResponseError):
            self.tvdb.search('something')

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

    def test_get_episode_requires_api_key(self):
        with self.assertRaises(APIKeyRequiredError):
            self.tvdb.get_episode(80348, 1, 1)


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

    def test_get_series_by_id_full_data(self):
        self.response(filename='80348.zip', content_type='application/zip')
        result = self.tvdb.get_series_by_id(80348, full_record=True)

        self.assertIsInstance(result, Series)
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/series/80348/all/en.zip',
            params={})
        # check episodes were loaded
        self.assertEqual(len(result.seasons), 6)
        self.assertEqual(len(result.seasons[1]), 13)

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

    def test_get_episode(self):
        self.response(filename='episode.xml')
        result = self.tvdb.get_episode(80348, 1, 1)

        self.assertIsInstance(result, Episode)
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/series/80348/default/1/1/en.xml',
            params={})

    def test_get_episode_missing_data(self):
        self.response(filename='empty.xml')
        result = self.tvdb.get_episode(80348, 6, 1)

        self.assertIsNone(result)
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/series/80348/default/6/1/en.xml',
            params={})

    def test_updated_without_timeframe_default_day(self):
        self.response(
            filename='updates_day.zip', content_type='application/zip')
        results = self.tvdb.updated()

        for result in results:
            self.assertIsInstance(result, Update)

        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/updates/updates_day.zip',
            params={})

    def test_updated_with_timeframe(self):
        self.response(
            filename='updates_month.zip', content_type='application/zip')
        results = self.tvdb.updated(TvDB.MONTH)

        for result in results:
            self.assertIsInstance(result, Update)

        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/123456789/updates/updates_month.zip',
            params={})

    def test_updated_with_invalid_timeframe(self):
        with self.assertRaises(TvDBException):
            self.tvdb.updated('anything')

    def test_updated_since_no_kind_specified(self):
        self.response(filename='updates_since.xml')
        results = self.tvdb.updated_since(1234567890)

        for result in results:
            self.assertIsInstance(result, Update)

        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/Updates.php?type=all&time=1234567890',
            params={})

    def test_updated_since_with_specific_kind(self):
        self.response(filename='updates_since_episodes.xml')
        results = self.tvdb.updated_since(1234567890, kind=TvDB.EPISODE)

        for result in results:
            self.assertIsInstance(result, Update)
            self.assertEqual(result.kind, TvDB.EPISODE)

        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/Updates.php?type=episode&time=1234567890',
            params={})

    def test_updated_since_with_invalid_kind(self):
        with self.assertRaises(TvDBException):
            self.tvdb.updated_since(123456780, 'anything')
