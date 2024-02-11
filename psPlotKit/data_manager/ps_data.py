import numpy as np
import quantities as qs
from psPlotKit.util import logger
import re

_logger = logger.define_logger(__name__, "psdata")
import time


class psData:
    def __init__(
        self,
        data_key,
        data_type,
        data_array,
        import_units,
        feasible_indexes=None,
        units=None,
        assign_units=None,
        conversion_factor=1,
        data_label=None,
        **kwargs
    ):
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
        to assigne any unit
        psData.assign_units(new_unit,manual_conversion_factor)
        """
        t = time.time()
        self._define_custom_units()
        self.data_key = data_key
        self.data_type = data_type
        self.data_label = data_key
        self.sunits = self._convert_string_unit(import_units)
        self.data = data_array
        if feasible_indexes is None:
            self.data_feasible = self.data
        else:
            self.data_feasible = self.data[feasible_indexes]
        self._assign_units()
        self.key_index = None
        self.key_index_str = None
        if assign_units != None:
            self.assign_units(assign_units, conversion_factor)
        if units != None:
            self.to_units(units)

    def _define_custom_units(self):
        qs.USD = qs.UnitQuantity("USD")
        qs.PPM = qs.UnitQuantity("PPM", qs.g / qs.m**3, symbol="PPM")
        self.custom_units = {"USD": qs.USD, "PPM": qs.PPM}

    def _assign_units(self, manual_conversion=1):
        self.data = self.data * manual_conversion
        self.data_feasible = self.data_feasible * manual_conversion
        qsunits = self._get_qs_unit()
        self.udata = qs.Quantity(self.data, qsunits)
        self.udata_feasible = qs.Quantity(self.data_feasible, qsunits)
        self.data = self.udata.magnitude
        self.data_feasible = self.udata_feasible.magnitude
        self.set_label()

    def set_label(self, label=None):
        if label != None:
            self.data_label = label
        units = self.sunits
        if "**" in self.sunits:
            uf = units.split("/")
            for i, u in enumerate(uf):
                if "**" in u:
                    u_t = u.replace("**", "^")
                    uf[i] = "${}$".format(u_t)
                if "USD" in u:
                    uf[i] = "$\$$"

            units = "/".join(uf)
        self.mpl_units = units

    def _get_qs_unit(self):
        if self.sunits not in self.custom_units:
            qsunits = self.sunits
        else:
            qsunits = self.custom_units[self.sunits]
        return qsunits

    def _convert_string_unit(self, units):
        if "USD" in units:
            uf = units.split("/")
            for i, u in enumerate(uf):
                if "USD" in u:
                    uf[i] = "USD"
            units = "/".join(uf)
            _logger.info("converted USD orig: {}, final {}".format(uf, units))
        if "1/a" in units:
            units = "1/year"
            _logger.info("converted 1/a to 1/year")
        if "gal" in units:
            units = units.replace("gal", "gallon")
            _logger.info("converted gal to gallon")
        return units
        # except AssertionError:
        #     _logger.warning(
        #         "Could not define units for {}, using dimensionless".format(units)
        #     )
        #     return "dimensionless"

    def to_units(self, new_units):
        self.sunits = self._convert_string_unit(new_units)
        qsunits = self._get_qs_unit()
        self.udata = self.udata.rescale(qsunits)
        self.data = self.udata.magnitude
        self.udata_feasible = self.udata_feasible.rescale(qsunits)
        self.data_feasible = self.udata_feasible.magnitude
        self.set_label()

    def assign_units(self, assigned_units, manual_conversion_factor=1):
        self.sunits = self._convert_string_unit(assigned_units)
        self._assign_units(manual_conversion=manual_conversion_factor)

    def display_data(self):
        _logger.info("Raw data: {}, units {}".format(self.udata))
