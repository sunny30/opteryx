"""
Test the connection example from the documentation
"""

import os
import sys

sys.path.insert(1, os.path.join(sys.path[0], "../.."))


def test_as_pandas_no_limit():
    import opteryx

    conn = opteryx.connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM $planets")
    table = cur.pandas()

    assert "name" in table.columns
    assert len(table) == 9
    assert len(table.columns) == 20


def test_as_pandas_with_limit():
    import opteryx

    conn = opteryx.connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM $planets")
    table = cur.pandas(size=5)

    assert "name" in table.columns
    assert len(table) == 5
    assert len(table.columns) == 20


if __name__ == "__main__":  # pragma: no cover
    from tests.tools import run_tests

    run_tests()
