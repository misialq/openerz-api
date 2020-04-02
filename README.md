### OpenERZ Python API

This wrapper allows you to interact with the OpenERZ API using Python code.

For more information about the API itself see: [http://openerz.metaodi.ch/documentation](http://openerz.metaodi.ch/documentation) and [https://github.com/metaodi/openerz](https://github.com/metaodi/openerz)

#### Usage example

A ready-to-run example can also be found in the `examples` directory.

```
from openerz_api.main import OpenERZConnector

ZIP = 8001
WASTE = "paper"

# initialize the connector given zip code and waste type
connector = OpenERZConnector(zip_code=ZIP, waste_type=WASTE)

# retrieve the next pick-up date within a period of choice
next_pickup = connector.find_next_pickup(day_offset=15)
```
