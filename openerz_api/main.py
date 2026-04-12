import logging
import requests
from datetime import datetime, timedelta


class OpenERZConnector:
    """A simple connector to interact with OpenERZ API."""

    BASE_URL = "https://openerz.metaodi.ch"
    STATION_MATERIALS = {"glass", "oil", "metal", "textile"}

    def __init__(self, zip_code=None, waste_type=None, region=None, area=None):
        """Initialize the API connector.

        Args:
        zip_code (int, optional): post code of the area of interest.
            Either this or region need to be set.
        waste_type (str): type of waste to be picked up
            (paper/cardboard/waste/cargotram/etram/organic/textile).
        region (str, optional): region key. Either this or zip_code needs to be set.
        area (str, optional): area label used to disambiguate collections
            within the same zip code.

        Raises:
        ValueError: If neither zip_code nor region is provided.
        ValueError: If waste_type is not provided.
        """
        if zip_code is None and region is None:
            raise ValueError("Either zip_code or region must be provided.")

        if waste_type is None:
            raise ValueError("Waste type must be provided.")

        self.zip = zip_code
        self.region = region
        self.area = area.lower() if isinstance(area, str) else area
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

    def build_calendar_payload(self):
        """Build the query parameters for the calendar endpoint."""

        start_date = self.start_date.strftime("%Y-%m-%d")
        end_date = self.end_date.strftime("%Y-%m-%d")

        return {
            "zip": self.zip,
            "region": self.region,
            "area": self.area,
            "types": self.waste_type,
            "start": start_date,
            "end": end_date,
            "offset": 0,
            "limit": 1,
            "lang": "en",
            "sort": "date",
        }

    @classmethod
    def fetch_json_result(cls, path, endpoint_name, params=None):
        """Fetch a JSON endpoint and return its result list."""

        headers = {"accept": "application/json"}
        filtered_params = None
        if params is not None:
            filtered_params = {
                key: value for key, value in params.items() if value is not None
            }
            if not filtered_params:
                filtered_params = None
        url = f"{cls.BASE_URL}{path}"
        logger = logging.getLogger(__name__)

        try:
            response = requests.get(url, params=filtered_params, headers=headers)
        except requests.exceptions.RequestException as connection_error:
            logger.error(
                "RequestException while making request to OpenERZ %s: %s",
                endpoint_name,
                connection_error,
            )
            return None

        if not response.ok:
            logger.warning(
                "Request to OpenERZ %s was not successful. Status code: %d",
                endpoint_name,
                response.status_code,
            )
            return None

        response_json = response.json()
        return response_json.get("result", [])

    @classmethod
    def fetch_parameter_values(cls, parameter_name, region=None):
        """Fetch available values from a parameter endpoint."""

        return cls.fetch_json_result(
            f"/api/parameter/{parameter_name}",
            f"parameter endpoint {parameter_name}",
            params={"region": region},
        )

    @classmethod
    def list_types(cls, region=None):
        """Return available waste types, optionally filtered by region."""

        return cls.fetch_parameter_values("types", region=region)

    @classmethod
    def list_regions(cls):
        """Return available regions."""

        return cls.fetch_parameter_values("regions")

    @classmethod
    def list_areas(cls, region=None):
        """Return available areas, optionally filtered by region."""

        return cls.fetch_parameter_values("areas", region=region)

    @classmethod
    def list_stations(
        cls,
        region=None,
        zip_code=None,
        name=None,
        materials=None,
        sort=None,
        offset=None,
        limit=None,
    ):
        """Return waste collection stations filtered by the given criteria."""

        material_params = {}
        if materials is not None:
            invalid_materials = []
            for material in materials:
                normalized_material = (
                    material.lower() if isinstance(material, str) else material
                )
                if normalized_material not in cls.STATION_MATERIALS:
                    invalid_materials.append(material)
                    continue
                material_params[normalized_material] = True

            if invalid_materials:
                raise ValueError(
                    "Unsupported station materials: "
                    + ", ".join(str(material) for material in invalid_materials)
                )

        return cls.fetch_json_result(
            "/api/stations.json",
            "stations endpoint",
            params={
                "region": region,
                "zip": zip_code,
                "name": name,
                "sort": sort,
                "offset": offset,
                "limit": limit,
                **material_params,
            },
        )

    def pickup_matches_configuration(self, pickup):
        """Check whether a pickup entry matches the configured filters."""

        expected_values = {
            "zip": self.zip,
            "region": self.region,
            "area": self.area,
            "waste_type": self.waste_type,
        }

        for key, expected_value in expected_values.items():
            if expected_value is None:
                continue
            if pickup.get(key) != expected_value:
                return False

        return True

    def make_api_request(self):
        """Construct a request and send it to the OpenERZ API."""

        headers = {"accept": "application/json"}
        payload = self.build_calendar_payload()
        url = f"{self.BASE_URL}/api/calendar.json"

        try:
            self.last_api_response = requests.get(url, params=payload, headers=headers)
        except requests.exceptions.RequestException as connection_error:
            self.logger.error(
                "RequestException while making request to OpenERZ: %s", connection_error
            )

    def parse_api_response(self):
        """Parse the JSON response received from the OpenERZ API
        and return a date of the next pickup."""

        if not self.last_api_response.ok:
            self.logger.warning(
                "Last request to OpenERZ was not successful. Status code: %d",
                self.last_api_response.status_code,
            )
            return None

        response_json = self.last_api_response.json()
        if response_json["_metadata"]["total_count"] == 0:
            self.logger.warning("Request to OpenERZ returned no results.")
            return None
        result_list = response_json.get("result")
        first_scheduled_pickup = result_list[0]
        if self.pickup_matches_configuration(first_scheduled_pickup):
            return first_scheduled_pickup["date"]
        self.logger.warning(
            "Either zip, region, area or waste type does not match the "
            "ones specified in the configuration."
        )
        return None

    def find_next_pickup(self, day_offset=31):
        """Find the next pickup date within the next X days,
            given zip_code and waste type

        Args:
        day_offset (int): difference in days between start and end date of the request
        """

        self.update_start_date()
        self.find_end_date(day_offset=day_offset)
        self.make_api_request()
        next_pickup_date = self.parse_api_response()
        return next_pickup_date
