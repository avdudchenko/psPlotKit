import numpy as np
import quantities as qs
from pint import UnitRegistry
from psPlotKit.util import logger

_logger = logger.define_logger(__name__, "psdata")
import time


class psData:
    def __init__(self, data_key, data_type, data_array, units, feasible_indexes):
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
        t = time.time()
        # self.ureg = UnitRegistry()
        qs.USD = qs.UnitQuantity("USD")
        # self.ureg.define("USD=1")
        # _logger.debug("ureg took: {}".format(time.time() - t))
        # self.ureg.define("a=year")
        self.data_key = data_key
        self.data_type = data_type
        self.sunits = self._convert_string_unit(units)
        self.data = data_array
        self.data_feasible = data_array[feasible_indexes]
        self.udata = qs.Quantity(data_array, self.sunits)
        self.udata_feasible = qs.Quantity(data_array[feasible_indexes])
        self.feasible_idx = feasible_indexes

    def _convert_string_unit(self, units):
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
            return units
        except AssertionError:
            _logger.warning(
                "Could not define units for {}, using dimensionless".format(units)
            )
            return "dimensionless"

    def to_units(self, new_units):
        self.udata.rescale(new_units)
        self.data = self.udata.magnitude
        self.udata_feasible.rescale(new_units)
        self.data_feasible = self.udata_feasible.magnitude

    def display_data(self):
        _logger.info("Raw data: {}, units {}".format(self.udata))
