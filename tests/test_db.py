import unittest
from unittest.mock import patch, MagicMock
from app.db.db import InfluxDBClient


class TestInfluxDBClient(unittest.TestCase):
    @patch("app.db.db.InfluxDBClient")
    def setUp(self, MockInfluxDBClient):
        self.mock_client = MockInfluxDBClient.return_value
        self.influxdb_client = InfluxDBClient("host", "token", "org", "database")

    def test_init(self):
        self.assertEqual(self.influxdb_client.host, "host")
        self.assertEqual(self.influxdb_client.token, "token")
        self.assertEqual(self.influxdb_client.org, "org")
        self.assertEqual(self.influxdb_client.database, "database")
        self.assertEqual(self.influxdb_client.verify_ssl, False)

    # @patch("db.Point")
    # def test_write_points_to_influxdb(self, MockPoint):
    #     mock_points = MagicMock()
    #     self.influxdb_client.write_points_to_influxdb(mock_points)
    #     self.mock_client.write.assert_called()
    #     MockPoint.assert_called_with("measurement")
    #     self.mock_client.write.assert_called_with(MockPoint.return_value)


if __name__ == "__main__":
    unittest.main()
