"""Tests for recognizing an MA Touch advertisement (no Home Assistant deps).

    pytest tests/test_discovery.py
"""

import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOD = os.path.join(_HERE, "..", "custom_components", "mitsubishi_matouch", "discovery.py")
_spec = importlib.util.spec_from_file_location("ma_discovery", _MOD)
d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d)

_OTHER_VENDOR_ADDRESS = "AA:BB:CC:00:00:01"


def test_factory_name_matches_at_any_address():
    assert d.is_matouch("M/R_CT01MAU_0A1B2C", _OTHER_VENDOR_ADDRESS, None)
    assert d.is_matouch("M/R_CT01MA_0A1B2C", _OTHER_VENDOR_ADDRESS, None)


def test_renamed_controller_matches_in_the_par_ct01mau_block():
    assert d.is_matouch("M/R_Bedroom", "58:52:8A:00:00:01", None)


def test_renamed_controller_matches_in_the_tar_ct01mau_block():
    assert d.is_matouch("M/R_Main", "28:E9:8E:00:00:01", None)


def test_renamed_controller_in_another_mitsubishi_electric_block_does_not_match():
    assert not d.is_matouch("M/R_Main", "10:4B:46:00:00:01", None)


def test_address_and_name_prefix_ignore_case():
    assert d.is_matouch("m/r_main", "28:e9:8e:00:00:01", None)


def test_renamed_name_at_another_vendors_address_does_not_match():
    assert not d.is_matouch("M/R_Main", _OTHER_VENDOR_ADDRESS, None)


def test_mitsubishi_electric_address_without_the_name_prefix_does_not_match():
    assert not d.is_matouch("Main", "28:E9:8E:00:00:01", None)
    assert not d.is_matouch(None, "28:E9:8E:00:00:01", None)


def test_service_uuid_matches_without_a_name():
    assert d.is_matouch(None, _OTHER_VENDOR_ADDRESS, [d.MA_TOUCH_SERVICE_UUID])
    assert not d.is_matouch(None, _OTHER_VENDOR_ADDRESS, [])
