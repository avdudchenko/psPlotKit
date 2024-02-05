import numpy as np
import quantities as qs
from pint import UnitRegistry
from psPlotKit.util import logger

_logger = logger.define_logger(__name__, "psdata")


class psData:
    def __init__(self, data_array, units, feasible_indexes):
        """
        This defines base ps data class and will store raw data and data with units
        conversions will be performed on raw and unit specific data if requested
        access data as follows

        psData.data - return raw numpy array
        psData.udata - return np array with units
        psData.data_feasible - returns only feasible data
        psData.udata_feasible - returns only feasible data with units

        to convert units
        psData.convert_units('new_unit')
        """
        self.ureg = UnitRegistry()
        self.ureg.define("USD=1")
        # self.ureg.define("a=year")
        self.data = data_array
        self.data_feasible = data_array[feasible_indexes]
        self.udata = data_array * self._convert_string_unit_to_pint(units)
        self.udata_feasible = data_array[
            feasible_indexes
        ] * self._convert_string_unit_to_pint(units)
        self.sunits = units
        self.feasible_idx = feasible_indexes

    def _convert_string_unit_to_pint(self, units):
        if "USD" in units:
            uf = units.split("/")
            for i, u in enumerate(uf):
                if "USD" in u:
                    uf[i] = "USD"
            units = "/".join(uf)
            _logger.debug("converted USD orig: {}, final {}".format(uf, units))
        elif "1/a" in units:
            units = "1/year"
        try:
            return self.ureg(units)
        except AssertionError:
            _logger.warning(
                "Could not define units for {}, using dimensionless".format(units)
            )
            return self.ureg("dimensionless")

    def convert_units(self, new_units):
        self.udata.to(new_units)
        self.data = self.udata.magnitude
        self.udata_feasible.to(new_units)
        self.data_feasible = self.udata_feasible.magnitude

    def display_data(self):
        _logger.info("Raw data: {}, units {}".format(self.udata))
