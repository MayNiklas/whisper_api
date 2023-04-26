import pytest


def test_always_passes():
    assert 1 == 1


def test_always_fails():
    pytest.fail("This test always fails")
