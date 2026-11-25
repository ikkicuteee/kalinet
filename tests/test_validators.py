import pytest

from app.utils.validators import validate_count, validate_target


@pytest.mark.parametrize("target", ["127.0.0.1", "192.0.2.1", "::1", "2001:db8::1", "localhost",
                                    "example.com", "example.com.", "my-host.lab", "xn--bcher-kva.example"])
def test_valid_targets(target):
    assert validate_target(target) == target


@pytest.mark.parametrize("target", ["", " ", " example.com", "example.com\n", "256.1.1.1", "1.2.3",
    "2001:::1", "-c", "@resolver", "+trace", "https://example.com", "192.0.2.0/24", "a;id",
    "$(id)", "a b", "a\x00b", "a..b", "a_.com", "-a.com", "a-.com", "a" * 64 + ".com",
    "fe80::1%eth0", "*.example.com", ".", "éxample.com"])
def test_invalid_targets(target):
    with pytest.raises(ValueError):
        validate_target(target)


@pytest.mark.parametrize("count", [0, 21, True, "4", 2.5])
def test_invalid_count(count):
    with pytest.raises(ValueError):
        validate_count(count)
