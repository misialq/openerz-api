from datetime import datetime
from unittest.mock import patch

from requests.exceptions import RequestException
from testfixtures import LogCapture
from openerz_api.main import OpenERZConnector

MOCK_DATETIME = datetime(year=2019, month=12, day=10, hour=11, minute=15, second=0, microsecond=0)


class MockAPIResponse:
    """Provide fake response from the OpenERZ API."""

    def __init__(self, is_ok, status_code, json_data):
        """Initialize all the values."""
        self.ok = is_ok
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        """Return response data."""
        return self.json_data


def setup_method():
    """Set up things to be run when tests are started."""
    return MOCK_DATETIME, 1234, "glass"


def assertDictEqual(dict1, dict2):
    assert len(dict1) == len(dict2)
    for key in dict1.keys():
        assert dict1[key] == dict2[key]


def test_init():
    """Test whether all values initialized properly."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.datetime") as patched_time:
        patched_time.now.return_value = mock_datetime

        test_openerz = OpenERZConnector(zip_code, waste_type)

        assert test_openerz.zip == 1234
        assert test_openerz.waste_type == "glass"
        assert test_openerz.start_date == mock_datetime
        assert test_openerz.end_date is None
        assert test_openerz.last_api_response is None


def test_sensor_update_start_date():
    """Test whether start date is updated correctly."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.datetime") as patched_time:
        patched_time.now.return_value = mock_datetime
        test_openerz = OpenERZConnector(zip_code, waste_type)

        patched_time.now.return_value = mock_datetime.replace(day=11)
        test_openerz.update_start_date()

        expected_start_date = datetime(year=2019, month=12, day=11, hour=11, minute=15, second=0, microsecond=0)
        assert test_openerz.start_date == expected_start_date


def test_sensor_find_end_date():
    """Test whether end date is correctly set."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.datetime") as patched_time:
        patched_time.now.return_value = mock_datetime
        test_openerz = OpenERZConnector(zip_code, waste_type)

        test_openerz.find_end_date()

        expected_end_date = datetime(year=2020, month=1, day=10, hour=11, minute=15, second=0, microsecond=0)
        assert test_openerz.end_date == expected_end_date


def test_sensor_make_api_request():
    """Test making API requests."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.requests") as patched_requests:
        patched_requests.get.return_value = {}
        with patch("openerz_api.main.datetime") as patched_time:
            patched_time.now.return_value = mock_datetime
            test_openerz = OpenERZConnector(zip_code, waste_type)
            test_openerz.end_date = mock_datetime.replace(year=2020, month=1, day=10)
            test_openerz.make_api_request()

            expected_headers = {"accept": "application/json"}
            expected_url = "http://openerz.metaodi.ch/api/calendar/glass.json"
            expected_payload = {
                "zip": 1234,
                "start": "2019-12-10",
                "end": "2020-01-10",
                "offset": 0,
                "limit": 1,
                "lang": "en",
                "sort": "date",
            }
            used_args, used_kwargs = patched_requests.get.call_args_list[0]
            assert used_args[0] == expected_url
            assertDictEqual(used_kwargs["headers"], expected_headers)
            assertDictEqual(used_kwargs["params"], expected_payload)


def test_sensor_make_api_request_connection_error():
    """Test making API requests."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.requests.get") as patched_get:
        patched_get.side_effect = RequestException("Connection timed out")
        with patch("openerz_api.main.datetime") as patched_time:
            patched_time.now.return_value = mock_datetime
            test_openerz = OpenERZConnector(zip_code, waste_type)
            test_openerz.end_date = mock_datetime.replace(year=2020, month=1, day=10)
            with LogCapture() as captured_logs:
                test_openerz.make_api_request()
                captured_logs.check_present(
                    (
                        "openerz_api.main",
                        "ERROR",
                        "RequestException while making request to OpenERZ: Connection timed out",
                    ),
                    order_matters=False,
                )


def test_sensor_parse_api_response_ok():
    """Test whether API response is parsed correctly."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.datetime") as patched_time:
        patched_time.now.return_value = mock_datetime
        test_openerz = OpenERZConnector(zip_code, waste_type)
        test_openerz.end_date = mock_datetime.replace(year=2020, month=1, day=10)

        response_data = {
            "_metadata": {"total_count": 1},
            "result": [{"zip": 1234, "type": "glass", "date": "2020-01-10"}],
        }
        test_openerz.last_api_response = MockAPIResponse(True, 200, response_data)

        test_pickup_date = test_openerz.parse_api_response()
        assert test_pickup_date == "2020-01-10"


def test_sensor_parse_api_response_no_data():
    """Test whether API response is parsed correctly when no data returned."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.datetime") as patched_time:
        patched_time.now.return_value = mock_datetime
        test_openerz = OpenERZConnector(zip_code, waste_type)
        test_openerz.end_date = mock_datetime.replace(year=2020, month=1, day=10)

        response_data = {"_metadata": {"total_count": 0}, "result": []}

        with LogCapture() as captured_logs:
            test_openerz.last_api_response = MockAPIResponse(True, 200, response_data)

            test_pickup_date = test_openerz.parse_api_response()
            assert test_pickup_date is None
            captured_logs.check_present(("openerz_api.main", "WARNING", "Request to OpenERZ returned no results.",))


def test_sensor_parse_api_response_wrong_zip():
    """Test handling unexpected zip in API response."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.datetime") as patched_time:
        patched_time.now.return_value = mock_datetime
        test_openerz = OpenERZConnector(zip_code, waste_type)
        test_openerz.end_date = mock_datetime.replace(year=2020, month=1, day=10)

        response_data = {
            "_metadata": {"total_count": 1},
            "result": [{"zip": 1235, "type": "glass", "date": "2020-01-10"}],
        }

        with LogCapture() as captured_logs:
            test_openerz.last_api_response = MockAPIResponse(True, 200, response_data)

            test_pickup_date = test_openerz.parse_api_response()
            assert test_pickup_date is None
            captured_logs.check_present(
                (
                    "openerz_api.main",
                    "WARNING",
                    "Either zip or waste type does not match the ones specified in the configuration.",
                )
            )


def test_sensor_parse_api_response_wrong_type():
    """Test handling unexpected waste type in API response."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.datetime") as patched_time:
        patched_time.now.return_value = mock_datetime
        test_openerz = OpenERZConnector(zip_code, waste_type)
        test_openerz.end_date = mock_datetime.replace(year=2020, month=1, day=10)

        response_data = {
            "_metadata": {"total_count": 1},
            "result": [{"zip": 1234, "type": "metal", "date": "2020-01-10"}],
        }

        with LogCapture() as captured_logs:
            test_openerz.last_api_response = MockAPIResponse(True, 200, response_data)

            test_pickup_date = test_openerz.parse_api_response()
            assert test_pickup_date is None
            captured_logs.check_present(
                (
                    "openerz_api.main",
                    "WARNING",
                    "Either zip or waste type does not match the ones specified in the configuration.",
                )
            )


def test_sensor_parse_api_response_not_ok():
    """Test handling of an erroneous API response."""
    mock_datetime, zip_code, waste_type = setup_method()
    with patch("openerz_api.main.datetime") as patched_time:
        patched_time.now.return_value = mock_datetime
        test_openerz = OpenERZConnector(zip_code, waste_type)
        test_openerz.end_date = mock_datetime.replace(year=2020, month=1, day=10)

        response_data = {"result": [{}]}

        with LogCapture() as captured_logs:
            test_openerz.last_api_response = MockAPIResponse(False, 404, response_data)

            test_pickup_date = test_openerz.parse_api_response()
            assert test_pickup_date is None
            captured_logs.check_present(
                ("openerz_api.main", "WARNING", "Last request to OpenERZ was not successful. Status code: 404",)
            )
