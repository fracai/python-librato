import sys, json, unittest, re
import librato
from mock_connection import MockRequest

librato.connection.requests = MockRequest()

class TestConnection(unittest.TestCase):
  def setUp(self):
    self.api = librato.Connection("drio", "abcdef")

  def tearDown(self):
    pass

  def test_init(self):
    assert type(self.api) == librato.Connection

  def test_get_list_all_metrics(self):
    results = self.api.list_metrics()
    assert type(results) == list
    assert len(results)  == 2
    for m in results:
      assert re.search('app_requests|server_temperature', m.name)
      if m.name == 'app_requests':
        assert m.type == 'counter'
        assert m.description == 'Number of HTTP requests serviced by the app'
        assert len(m.attributes) == 0
      if m.name == 'server_temperature':
        assert m.type == 'gauge'
        assert m.description == 'Temperature of the server as measured in degrees Fahrenheit'
        assert len(m.attributes) == 1
        assert m.attributes['display_max'] == 150

  def test_get_specific_metric(self):
    expected_name = 'app_requests'
    results = self.api.list_metrics(name=expected_name)
    assert len(results) == 1
    assert results[0].name == expected_name

if __name__ == '__main__':
  unittest.main()