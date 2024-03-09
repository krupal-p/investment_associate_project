from datetime import datetime

from utils import get_alpha_vantage_historical_data, get_realtime_quote


def test_get_alpha_vantage_historical_data():
    df = get_alpha_vantage_historical_data("AAPL", 60)

    assert df.size > 0
    assert "datetime" in df.columns
    assert "price" in df.columns

    # df = get_alpha_vantage_historical_data("AAPL", 13434)
    # assert df.empty

    # df = get_alpha_vantage_historical_data("AdsfdfAPL", 5)
    # assert df.empty


def test_get_realtime_quote():
    data = get_realtime_quote("AAPL")

    assert data is not None
    assert type(data["price"]) == float
    assert type(data["datetime"]) == datetime
