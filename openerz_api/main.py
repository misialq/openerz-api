import logging
import requests
from datetime import datetime, timedelta


class OpenERZConnector:
    """A simple connector to interact with OpenERZ API."""

    def __init__(self, zip_code, waste_type):
        """Initialize the API connector.
        
        Args:
        zip_code (int): post code of the area of interest
        waste_type (str): type of waste to be picked up (paper/cardboard/waste/cargotram/etram/organic/textile)
        """
        self.zip = zip_code
        self.waste_type = waste_type
        self.start_date = datetime.now()
        self.end_date = None
        self.last_api_response = None
        self.logger = logging.getLogger(__name__)

    def update_start_date(self):
        """Set the start day to today."""

        self.start_date = datetime.now()

    def find_end_date(self, day_offset=31):
        """Find the end date for the request, given an offset expressed in days.

        Args:
        day_offset (int): difference in days between start and end date of the request
        """

        self.end_date = self.start_date + timedelta(days=day_offset)

    def make_api_request(self):
        """Construct a request and send it to the OpenERZ API."""

        headers = {"accept": "application/json"}

        start_date = self.start_date.strftime("%Y-%m-%d")
        end_date = self.end_date.strftime("%Y-%m-%d")

        payload = {
            "zip": self.zip,
            "start": start_date,
            "end": end_date,
            "offset": 0,
            "limit": 0,
            "lang": "en",
            "sort": "date",
        }
        url = f"http://openerz.metaodi.ch/api/calendar/{self.waste_type}.json"

        try:
            self.last_api_response = requests.get(url, params=payload, headers=headers)
        except requests.exceptions.RequestException as connection_error:
            self.logger.error("RequestException while making request to OpenERZ: %s", connection_error)

    def parse_api_response(self):
        """Parse the JSON response received from the OpenERZ API and return a date of the next pickup."""

        if not self.last_api_response.ok:
            self.logger.warning(
                "Last request to OpenERZ was not successful. Status code: %d", self.last_api_response.status_code,
            )
            return None

        response_json = self.last_api_response.json()
        if response_json["_metadata"]["total_count"] == 0:
            self.logger.warning("Request to OpenERZ returned no results.")
            return None
        result_list = response_json.get("result")
        first_scheduled_pickup = result_list[0]
        if first_scheduled_pickup["zip"] == self.zip and first_scheduled_pickup["type"] == self.waste_type:
            return first_scheduled_pickup["date"]
        self.logger.warning("Either zip or waste type does not match the ones specified in the configuration.")
        return None

    def find_next_pickup(self, day_offset=31):
        """Find the next pickup date within the next X days, given zip_code and waste type

        Args:
        day_offset (int): difference in days between start and end date of the request
        """

        self.update_start_date()
        self.find_end_date(day_offset=day_offset)
        self.make_api_request()
        next_pickup_date = self.parse_api_response()
        return next_pickup_date
