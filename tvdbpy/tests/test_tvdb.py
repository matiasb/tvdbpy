import codecs
import os
import unittest
import xml.etree.ElementTree as ET

from datetime import date
from io import BytesIO

import mock
import requests

from tvdbpy import TvDB
from tvdbpy.errors import APIResponseError
from tvdbpy.tvdb import SearchResult


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

    def response(self, url=None, method='GET', status_code=200, filename=None):
        """Set a custom response from a file."""
        data = None
        if filename is not None:
            path = os.path.join(TESTS_DIR, 'xml', filename)
            with codecs.open(path, 'r', 'utf-8') as xml:
                data = xml.read()

        response = requests.Response()
        response.status_code = status_code

        if data is not None:
            response.encoding = 'utf-8'
            response.headers['content-type'] = 'text/xml; charset=utf-8'
            response.raw = RequestsBytesIO(data.encode('utf-8'))

        requests_method = getattr(self.requests, method.lower())
        setattr(requests_method, 'return_value', response)


class TvDBSearchResultTestCase(BaseTestCase):
    """Test search result instance."""

    def setUp(self):
        super(TvDBSearchResultTestCase, self).setUp()
        self.response(url='http://thetvdb.com/api/GetSeries.php',
                      filename='getseries.xml')
        tvdb = TvDB()
        results = tvdb.search('chuck')
        self.result = results[0]

    def test_search_result_from_xml(self):
        xml = """
            <Series>
                <seriesid>80348</seriesid>
                <SeriesName>Chuck</SeriesName>
                <banner>graphical/80348-g32.jpg</banner>
                <Overview>description</Overview>
                <FirstAired>2007-09-24</FirstAired>
                <IMDB_ID>tt0934814</IMDB_ID>
            </Series>"""
        result = SearchResult(ET.fromstring(xml))
        self.assertEqual(self.result.id, '80348')
        self.assertEqual(self.result.name, 'Chuck')
        # when not available, field is None
        self.assertIsNone(result.network)
        # client is not set since result was not generated from search
        self.assertIsNone(result._client)

    def test_is_search_result(self):
        self.assertIsInstance(self.result, SearchResult)

    def test_search_result_attrs(self):
        expected = ['id', 'imdb_id', 'name', 'overview', 'language',
                    'first_aired', 'network', 'banner']
        for attr in expected:
            unexpected = object()
            value = getattr(self.result, attr, unexpected)
            self.assertNotEqual(value, unexpected)

    def test_search_result_values(self):
        self.assertEqual(self.result.id, '80348')
        self.assertEqual(self.result.name, 'Chuck')
        self.assertEqual(self.result.first_aired, date(2007, 9, 24))
        self.assertEqual(
            self.result.banner,
            'http://thetvdb.com/banners/graphical/80348-g32.jpg')

    def test_search_result_client_set(self):
        self.assertIsNotNone(self.result._client)


class TvDBTestCase(BaseTestCase):
    """TvDB client test case."""

    def setUp(self):
        super(TvDBTestCase, self).setUp()
        self.tvdb = TvDB()

    def test_response_error(self):
        self.response(status_code=404)

        with self.assertRaises(APIResponseError):
            results = self.tvdb.search('something')

    def test_response_unexpected_content_type(self):
        self.response(status_code=200)

        with self.assertRaises(APIResponseError):
            results = self.tvdb.search('something')

    def test_search_no_results(self):
        self.response(url='http://thetvdb.com/api/GetSeries.php',
                      filename='getseries_no_results.xml')

        results = self.tvdb.search('nothing')

        self.assertEqual(results, [])
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/GetSeries.php',
            params={'seriesname': 'nothing'})

    def test_search_results(self):
        self.response(url='http://thetvdb.com/api/GetSeries.php',
                      filename='getseries.xml')

        results = self.tvdb.search('chuck')

        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/GetSeries.php',
            params={'seriesname': 'chuck'})
        self.assertEqual(len(results), 7)
