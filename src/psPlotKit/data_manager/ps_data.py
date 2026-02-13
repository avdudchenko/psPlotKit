import numpy as np
import quantities as qs
from psPlotKit.util import logger
import re
import copy

__author__ = "Alexander V. Dudchenko (SLAC)"

_logger = logger.define_logger(__name__, "PsData", level="INFO")
import time
import datetime


class CustomUnits:
    def __init__(self):
        self.USD = qs.UnitQuantity("USD")
        self.PPM = qs.UnitQuantity("PPM", qs.g / qs.m**3, symbol="PPM")
        self.custom_units = {"USD": self.USD, "PPM": self.PPM}

    def get_units_dict(self):
        return self.custom_units


class PsData:
    def __init__(
        self,
        data_key,
        data_type,
        data_array,
        import_units="dimensionless",
        feasible_indexes=None,
        units=None,
        assign_units=None,
        conversion_factor=1,
        data_label=None,
        custom_units=None,
        **kwargs,
    ):
        """
        This defines base ps data class and will store raw data and data with units
        conversions will be performed on raw and unit specific data if requested
        access data as follows

        PsData.data - return raw numpy array
        PsData.data_with_units - return np array with units (also available as .udata for backwards compatibility)
        PsData.data_feasible - returns only feasible data
        PsData.raw_data_with_units - returns raw data with units (also available as .uraw_data for backwards compatibility)

        to convert units
        PsData.convert_units('new_unit')
        to assigne any unit
        PsData.assign_units(new_unit,manual_conversion_factor)
        """
        self._define_custom_units(custom_units)
        self.data_key = data_key
        self.data_type = data_type
        self._convert_iso_to_epoch = False

        if data_label == None:
            self.data_label = data_key
        else:
            self.data_label = data_label
        # Accept quantities objects directly — extract magnitude and units
        if isinstance(data_array, qs.Quantity):
            import_units = str(data_array.dimensionality)
            data_array = data_array.magnitude
        self.sunits = self._convert_string_unit(import_units)
        self.data_is_numbers = True
        self._original_data = np.array(data_array).copy()
        self._raw_data = self._original_data.copy()
        if self._convert_iso_to_epoch:
            data_array = np.array(self._iso_to_epoch(data_array))
        if isinstance(data_array, list):
            try:
                data_array = np.array(data_array, dtype=float)
            except:
                data_array = np.array(data_array, dtype=str)
                self.data_is_numbers = False
        self.raw_data = data_array.copy()
        self.data = data_array.copy()
        self.feasible_indexes = feasible_indexes
        self._assign_units()
        self.key_index = None
        self.key_index_str = None
        if assign_units != None:
            self.assign_units(assign_units, conversion_factor)
        if units != None:
            self.to_units(units)

    def get_data(self, exclude_nan_values=False):
        if exclude_nan_values:
            return self.data[~np.isnan(self.data)]
        else:
            return self.data

    def get_raw_data(self, exclude_nan_values=False):
        if exclude_nan_values:
            return self.raw_data[~np.isnan(self.raw_data)]
        else:
            return self.raw_data

    def get_feasible_data(self):
        if self.feasible_indexes is not None:
            return self.data[self.feasible_indexes]
        else:
            return self.data

    def mask_data(self, user_filter=None, feasible_only=False):
        """will reduce data with provided filter
        user_filter must have a data object, filter_type object, and data_shape object
        e.g.
        user_filter.data - return indexes to use for filter
        user_filter.filter_type - defines type of filtering
        user_filter.data_shape - defines excat shape of input data

        if filter type is not supported or found, skipes filtering without warnings enable debug log to see
        errors"""
        if feasible_only:
            if self.raw_data.shape == self.feasible_indexes.shape:
                self.data = self.raw_data.copy()[self.feasible_indexes]
                self._raw_data = self._original_data.copy()[self.feasible_indexes]
                self._assign_units()
        if user_filter is not None:
            if user_filter.filter_type == "2D":
                self.data = self.raw_data.copy()
                try:
                    self.data = self._take_along(self.data, user_filter.data)
                except:
                    pass

                self._raw_data = self._original_data.copy()
                try:
                    self._raw_data = self._take_along(self._raw_data, user_filter.data)
                except:
                    pass
                self._assign_units()
            elif user_filter.filter_type == "1D":
                self.data = self.raw_data.copy()[user_filter.data]
                self._raw_data = self._original_data.copy()[user_filter.data]
                self._assign_units()
            else:
                _logger.debug(
                    "User filter not found type:{} data shape {}".format(
                        user_filter.filter_type, user_filter.filter_data_shape
                    )
                )

    def _take_along(self, data, idxs):
        reduced_data = []
        for i, fidx in enumerate(idxs):
            if fidx == fidx:

                dt = data[:, i]
                reduced_data.append(dt[int(fidx)])
            else:
                reduced_data.append(np.nan)
        return np.array(reduced_data)

    def _define_custom_units(self, custom_units=None):
        if custom_units is None:
            custom_units = CustomUnits()
        self.custom_units = custom_units.get_units_dict()

    def _assign_units(self, manual_conversion=1):
        if self.data_is_numbers:
            self.data = self.data * manual_conversion
        qsunits = self._get_qs_unit()
        self.data_with_units = qs.Quantity(self.data.copy(), qsunits)
        self.raw_data_with_units = qs.Quantity(self.raw_data.copy(), qsunits)
        self.data = self.data_with_units.magnitude
        self.set_label()

    @property
    def udata(self):
        """Backwards-compatible alias for data_with_units."""
        return self.data_with_units

    @udata.setter
    def udata(self, value):
        self.data_with_units = value

    @property
    def uraw_data(self):
        """Backwards-compatible alias for raw_data_with_units."""
        return self.raw_data_with_units

    @uraw_data.setter
    def uraw_data(self, value):
        self.raw_data_with_units = value

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
        if "dimensionless" in self.sunits:
            units = "-"
        self.mpl_units = units

    def _get_qs_unit(self):
        if self.sunits not in self.custom_units:
            try:
                qsunits = self.sunits
            except LookupError:
                # _logger.info("created custom unit {}".format(self.sunits))
                self.custom_units[self.sunits] = qs.UnitQuantity(self.sunits)
                qsunits = self.custom_units[self.sunits]
        else:
            qsunits = self.custom_units[self.sunits]
        return qsunits

    def _convert_string_unit(self, units):
        if units is None or units == "-":
            return "dimensionless"
        if "isotime" in units:
            units = "min"
            _logger.info("Imported ISO time - converted to epoch time in min")
            self._convert_iso_to_epoch = True
        if "USD" in units:
            uf = units.split("/")
            for i, u in enumerate(uf):
                if "USD" in u:
                    uf[i] = "USD"
            units = "/".join(uf)
            _logger.debug("converted USD orig: {}, final {}".format(uf, units))
        if "USD/a" in units:
            units = "USD/year"
            _logger.debug("converted USD orig: {}, final {}".format(uf, units))

        if "1/a" in units:
            units = "1/year"
            _logger.debug("converted 1/a to 1/year")
        if "PSI" in units:
            units = units.replace("PSI", "psi")
            _logger.debug("converted gal to gallon")
        if "gal" in units:
            units = units.replace("gal", "US_liquid_gallon")
            _logger.debug("converted gal to gallon")
        if "gpm" in units:
            units = units.replace("gpm", "US_liquid_gallon/min")
            _logger.debug("converted gal to gallon")
        if "°C" in units:
            units = units.replace(" °C", "*degC")
            _logger.debug("converted C to degC")
        if "liter" in units:
            units = units.replace("liter", "L")
        if "sec" in units:
            units = units.replace("sec", "s")
        return units

    def set_data(self, data):
        self.data = data
        self.raw_data = data

    def to_units(self, new_units):
        self.sunits = self._convert_string_unit(new_units)
        qsunits = self._get_qs_unit()
        if new_units == "degC" and str(self.data_with_units.units) == "1.0 K":
            self.data_with_units = qs.Quantity(
                self.data_with_units.magnitude[:] - 273.15, new_units
            )
        else:
            self.data_with_units = self.data_with_units.rescale(qsunits)
        self.raw_data_with_units = self.raw_data_with_units.rescale(qsunits)
        self.data = self.data_with_units.magnitude[:]
        self.raw_data = self.raw_data_with_units.magnitude
        self.set_label()
        return self

    def assign_units(self, assigned_units, manual_conversion_factor=1):
        self.sunits = self._convert_string_unit(assigned_units)
        self._assign_units(manual_conversion=manual_conversion_factor)

    def display(self):
        _logger.info("Data: {}, units {}".format(self.data, self.sunits))

    def display_raw_data(self):
        _logger.info(
            "Raw data: {}, units {}".format(self.raw_data_with_units, self.sunits)
        )

    def _iso_to_epoch(self, data):
        # data_time = map(data, datetime.time.fromisoformat)
        epoch_time = [
            datetime.datetime.fromisoformat(dt).timestamp() / 60 for dt in data
        ]
        return epoch_time

    def get_json_dict(self, raw=False):
        data_dict = {}
        data_dict["units"] = self.sunits
        if raw:
            data_dict["units"] = "raw data"
            data_dict["values"] = self._raw_data.tolist()
        else:
            data_dict["units"] = self.sunits
            data_dict["values"] = self.data.tolist()
        return data_dict

    # ---------- arithmetic operations ----------

    def _arithmetic_op(self, other, op, symbol):
        """Perform an arithmetic operation between two PsData objects.

        Uses data_with_units so the quantities library handles unit
        compatibility and propagation.  Returns a new PsData whose
        data_key describes the operation performed.

        Args:
            other: another PsData instance.
            op: callable that takes (self.data_with_units, other.data_with_units).
            symbol: string like '+', '-', '*', '/' used in the result data_key.
        """
        if not isinstance(other, PsData):
            raise TypeError(
                "Arithmetic operations require two PsData objects, "
                "got {}".format(type(other))
            )
        result_quantity = op(self.data_with_units, other.data_with_units)
        result_key = "({} {} {})".format(self.data_key, symbol, other.data_key)
        return PsData(
            data_key=result_key,
            data_type="arithmetic_result",
            data_array=result_quantity,
        )

    def __add__(self, other):
        return self._arithmetic_op(other, lambda a, b: a + b, "+")

    def __sub__(self, other):
        return self._arithmetic_op(other, lambda a, b: a - b, "-")

    def __mul__(self, other):
        return self._arithmetic_op(other, lambda a, b: a * b, "*")

    def __truediv__(self, other):
        return self._arithmetic_op(other, lambda a, b: a / b, "/")


class psData(PsData):
    _logger.warning("psData is deprecated, please use PsData")
