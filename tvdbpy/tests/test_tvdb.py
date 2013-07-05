import codecs
import os
import unittest

from io import BytesIO

import mock
import requests

from tvdbpy import TvDB
from tvdbpy.errors import APIResponseError


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

        self.assertEqual(len(results), 7)
        self.requests.get.assert_called_once_with(
            'http://thetvdb.com/api/GetSeries.php',
            params={'seriesname': 'chuck'})