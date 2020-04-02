from openerz_api.main import OpenERZConnector

ZIP = 8001
WASTE = "paper"

# initialize the connector given zip code and waste type
connector = OpenERZConnector(zip_code=ZIP, waste_type=WASTE)

# retrieve the next pick-up date within a period of choice
next_pickup = connector.find_next_pickup(day_offset=15)

print(f"Next pickup date for {WASTE} in {ZIP} area: {next_pickup}")
