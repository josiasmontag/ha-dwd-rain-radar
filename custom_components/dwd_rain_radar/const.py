"""DWD Rain Radar constants."""

from homeassistant.const import Platform

DOMAIN = "dwd_rain_radar"

ATTRIBUTION = "Data provided by Deutscher Wetterdienst (DWD)"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

CONF_COORDINATES = "coordinates"

DWD_OPENDATA_URL = "https://opendata.dwd.de"

DWD_RADAR_COMPOSITE_RV_URL = f"{DWD_OPENDATA_URL}/weather/radar/composite/rv/DE1200_RV_LATEST.tar.bz2"

FORECAST_MINUTES = [5, 10, 15, 20, 25, 30, 45, 60, 90, 120]
