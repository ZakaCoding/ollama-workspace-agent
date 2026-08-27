import pytest

from app.calculator import add, subtract, multiply, divide, power


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (2, 3, 5),
        (-2, 5, 3),
        (0, 0, 0),
    ],
)
def test_add(a, b, expected):
    assert add(a, b) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (5, 2, 3),
        (0, 3, -3),
        (-4, -2, -2),
    ],
)
def test_subtract(a, b, expected):
    assert subtract(a, b) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (3, 4, 12),
        (-2, 5, -10),
        (0, 9, 0),
    ],
)
def test_multiply(a, b, expected):
    assert multiply(a, b) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (10, 2, 5),
        (9, 3, 3),
        (7, 1, 7),
    ],
)
def test_divide(a, b, expected):
    assert divide(a, b) == expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (2, 3, 8),
        (5, 2, 25),
        (4, 0, 1),
    ],
)
def test_power(a, b, expected):
    assert power(a, b) == expected
