import pytest
import numpy as np
import quantities as qs
from psPlotKit.data_manager.ps_data import PsData

__author__ = "Alexander V. Dudchenko (SLAC)"


# ---------- fixtures ----------


@pytest.fixture
def simple_ps():
    """PsData with dimensionless data."""
    return PsData("x", "test", [1.0, 2.0, 3.0])


@pytest.fixture
def meter_ps():
    """PsData with meter units."""
    return PsData("length", "test", [10.0, 20.0, 30.0], import_units="m")


@pytest.fixture
def second_meter_ps():
    """Another PsData with meter units for binary ops."""
    return PsData("width", "test", [1.0, 2.0, 3.0], import_units="m")


@pytest.fixture
def usd_ps():
    """PsData with USD units."""
    return PsData("cost", "test", [100.0, 200.0, 300.0], import_units="USD")


# ---------- data_with_units refactor & backwards compat ----------


class TestDataWithUnitsRefactor:
    def test_data_with_units_exists(self, simple_ps):
        """data_with_units should be a quantities.Quantity object."""
        assert isinstance(simple_ps.data_with_units, qs.Quantity)

    def test_raw_data_with_units_exists(self, simple_ps):
        """raw_data_with_units should be a quantities.Quantity object."""
        assert isinstance(simple_ps.raw_data_with_units, qs.Quantity)

    def test_udata_alias_reads(self, simple_ps):
        """The .udata property should return the same object as data_with_units."""
        assert simple_ps.udata is simple_ps.data_with_units

    def test_uraw_data_alias_reads(self, simple_ps):
        """The .uraw_data property should return the same object as raw_data_with_units."""
        assert simple_ps.uraw_data is simple_ps.raw_data_with_units

    def test_udata_alias_writes(self):
        """Writing to .udata should update data_with_units."""
        ps = PsData("x", "test", [1.0])
        new_val = qs.Quantity([99.0], "m")
        ps.udata = new_val
        assert ps.data_with_units is new_val

    def test_uraw_data_alias_writes(self):
        """Writing to .uraw_data should update raw_data_with_units."""
        ps = PsData("x", "test", [1.0])
        new_val = qs.Quantity([99.0], "m")
        ps.uraw_data = new_val
        assert ps.raw_data_with_units is new_val

    def test_data_with_units_magnitude_matches_data(self, meter_ps):
        """data_with_units magnitude should equal .data."""
        np.testing.assert_array_almost_equal(
            meter_ps.data_with_units.magnitude, meter_ps.data
        )

    def test_to_units_updates_data_with_units(self, meter_ps):
        """After to_units, data_with_units should reflect the new unit."""
        meter_ps.to_units("cm")
        np.testing.assert_array_almost_equal(meter_ps.data, [1000.0, 2000.0, 3000.0])
        assert "cm" in str(meter_ps.data_with_units.dimensionality) or np.allclose(
            meter_ps.data_with_units.magnitude, [1000.0, 2000.0, 3000.0]
        )


# ---------- quantities input support ----------


class TestQuantitiesInput:
    def test_accept_quantity_array(self):
        """PsData should accept a quantities.Quantity as data_array and
        auto-extract magnitude and units."""
        q = qs.Quantity([5.0, 10.0, 15.0], "m")
        ps = PsData("length", "test", q)

        np.testing.assert_array_almost_equal(ps.data, [5.0, 10.0, 15.0])
        assert ps.sunits == "m"

    def test_accept_quantity_with_compound_units(self):
        """Compound units from a Quantity should be extracted correctly."""
        q = qs.Quantity([1.0, 2.0], "m/s")
        ps = PsData("speed", "test", q)

        np.testing.assert_array_almost_equal(ps.data, [1.0, 2.0])
        assert "m" in ps.sunits and "s" in ps.sunits

    def test_quantity_input_ignores_import_units_arg(self):
        """When data_array is a Quantity, its units should take precedence
        over the import_units argument."""
        q = qs.Quantity([3.0, 6.0], "kg")
        ps = PsData("mass", "test", q, import_units="should_be_ignored")

        assert "kg" in ps.sunits

    def test_quantity_input_then_convert(self):
        """Should be able to create from Quantity then convert units."""
        q = qs.Quantity([1000.0, 2000.0], "m")
        ps = PsData("distance", "test", q)
        ps.to_units("km")

        np.testing.assert_array_almost_equal(ps.data, [1.0, 2.0])

    def test_quantity_scalar(self):
        """A scalar Quantity should also work."""
        q = qs.Quantity(42.0, "s")
        ps = PsData("time", "test", q)

        assert ps.data == pytest.approx(42.0)
        assert ps.sunits == "s"


# ---------- arithmetic: addition ----------


class TestAddition:
    def test_add_same_units(self, meter_ps, second_meter_ps):
        result = meter_ps + second_meter_ps
        np.testing.assert_array_almost_equal(result.data, [11.0, 22.0, 33.0])

    def test_add_data_key_describes_operation(self, meter_ps, second_meter_ps):
        result = meter_ps + second_meter_ps
        assert "+" in result.data_key
        assert "length" in result.data_key
        assert "width" in result.data_key

    def test_add_returns_psdata(self, meter_ps, second_meter_ps):
        result = meter_ps + second_meter_ps
        assert isinstance(result, PsData)

    def test_add_preserves_units(self, meter_ps, second_meter_ps):
        result = meter_ps + second_meter_ps
        assert "m" in str(result.data_with_units.dimensionality)

    def test_add_non_psdata_raises(self, meter_ps):
        with pytest.raises(TypeError, match="PsData"):
            meter_ps + 5


# ---------- arithmetic: subtraction ----------


class TestSubtraction:
    def test_sub_same_units(self, meter_ps, second_meter_ps):
        result = meter_ps - second_meter_ps
        np.testing.assert_array_almost_equal(result.data, [9.0, 18.0, 27.0])

    def test_sub_data_key_describes_operation(self, meter_ps, second_meter_ps):
        result = meter_ps - second_meter_ps
        assert "-" in result.data_key
        assert "length" in result.data_key
        assert "width" in result.data_key

    def test_sub_returns_psdata(self, meter_ps, second_meter_ps):
        result = meter_ps - second_meter_ps
        assert isinstance(result, PsData)

    def test_sub_non_psdata_raises(self, meter_ps):
        with pytest.raises(TypeError, match="PsData"):
            meter_ps - [1, 2, 3]


# ---------- arithmetic: multiplication ----------


class TestMultiplication:
    def test_mul_dimensionless(self, meter_ps):
        factor = PsData("scale", "test", [2.0, 2.0, 2.0])
        result = meter_ps * factor
        np.testing.assert_array_almost_equal(result.data, [20.0, 40.0, 60.0])

    def test_mul_data_key_describes_operation(self, meter_ps):
        factor = PsData("scale", "test", [2.0, 2.0, 2.0])
        result = meter_ps * factor
        assert "*" in result.data_key
        assert "length" in result.data_key
        assert "scale" in result.data_key

    def test_mul_returns_psdata(self, meter_ps):
        factor = PsData("scale", "test", [2.0, 2.0, 2.0])
        result = meter_ps * factor
        assert isinstance(result, PsData)

    def test_mul_non_psdata_raises(self, meter_ps):
        with pytest.raises(TypeError, match="PsData"):
            meter_ps * 3.0


# ---------- arithmetic: division ----------


class TestDivision:
    def test_div_same_units(self, meter_ps, second_meter_ps):
        """Dividing same units should yield dimensionless result."""
        result = meter_ps / second_meter_ps
        np.testing.assert_array_almost_equal(result.data, [10.0, 10.0, 10.0])

    def test_div_data_key_describes_operation(self, meter_ps, second_meter_ps):
        result = meter_ps / second_meter_ps
        assert "/" in result.data_key
        assert "length" in result.data_key
        assert "width" in result.data_key

    def test_div_returns_psdata(self, meter_ps, second_meter_ps):
        result = meter_ps / second_meter_ps
        assert isinstance(result, PsData)

    def test_div_by_dimensionless(self, meter_ps):
        divisor = PsData("half", "test", [2.0, 2.0, 2.0])
        result = meter_ps / divisor
        np.testing.assert_array_almost_equal(result.data, [5.0, 10.0, 15.0])

    def test_div_non_psdata_raises(self, meter_ps):
        with pytest.raises(TypeError, match="PsData"):
            meter_ps / 2.0


# ---------- chained arithmetic ----------


class TestChainedArithmetic:
    def test_chain_add_sub(self, meter_ps, second_meter_ps):
        """(a + b) - b should equal a."""
        result = (meter_ps + second_meter_ps) - second_meter_ps
        np.testing.assert_array_almost_equal(result.data, meter_ps.data)

    def test_chain_mul_div(self, meter_ps):
        """(a * 2) / 2 should equal a."""
        two = PsData("two", "test", [2.0, 2.0, 2.0])
        result = (meter_ps * two) / two
        np.testing.assert_array_almost_equal(result.data, meter_ps.data, decimal=5)

    def test_chain_mul_div_convert(self, meter_ps):
        """(a * 2) / 2 should equal a."""
        two = PsData("two", "test", [2.0, 2.0, 2.0])
        result = (meter_ps * two) / two
        np.testing.assert_array_almost_equal(
            result.to_units("cm").data, meter_ps.to_units("cm").data, decimal=5
        )

    def test_chained_data_key_nests(self, meter_ps, second_meter_ps):
        """Chained ops should nest the data_key string."""
        result = (meter_ps + second_meter_ps) * meter_ps
        assert "+" in result.data_key
        assert "*" in result.data_key


# ---------- arithmetic with quantity-created PsData ----------


class TestArithmeticWithQuantityInput:
    def test_add_quantity_created(self):
        """PsData created from quantities objects should support arithmetic."""
        a = PsData("a", "test", qs.Quantity([1.0, 2.0], "m"))
        b = PsData("b", "test", qs.Quantity([3.0, 4.0], "m"))
        result = a + b
        np.testing.assert_array_almost_equal(result.data, [4.0, 6.0])

    def test_mul_quantity_created(self):
        """Multiplying quantity-created PsData objects should work."""
        a = PsData("a", "test", qs.Quantity([2.0, 3.0], "m"))
        b = PsData("b", "test", qs.Quantity([4.0, 5.0], "dimensionless"))
        result = a * b
        np.testing.assert_array_almost_equal(result.data, [8.0, 15.0])
