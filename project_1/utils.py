from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import Any

import finnhub
import pandas as pd
import requests
from logger import log

# Loads the config file for API keys
config = ConfigParser()
config.read(Path(__file__).parent / "config.txt")


ALPHA_VANTAGE_API_KEY = config["API_KEYS"]["ALPHA_VANTAGE_API_KEY"]
FINNHUB_API_KEY = config["API_KEYS"]["FINNHUB_API_KEY"]


def get_alpha_vantage_historical_data(ticker: str, interval: int) -> pd.DataFrame:
    """
    Retrieves historical data from the Alpha Vantage API for a given ticker symbol and interval.

    Args:
        ticker (str): The ticker symbol of the stock or asset.
        interval (int): The time interval for the historical data in minutes.

    Returns:
        pd.DataFrame: A DataFrame containing the historical data with columns 'datetime' and 'price',
                      sorted by datetime in ascending order.
    """
    log.info("Getting historical data from Alpha Vantage API for %s", ticker)

    alpha_vantage_url = "https://www.alphavantage.co/query?"
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": ticker,
        "interval": f"{interval}min",
        "outputsize": "full",
        "extended_hours": "false",
        "apikey": ALPHA_VANTAGE_API_KEY,
    }

    resp = requests.get(alpha_vantage_url, params=params)
    if resp.status_code == 200 and "Invalid API call" in resp.text:
        log.error(f"Invalid API call: {resp.text}")
        return pd.DataFrame()

    if (
        resp.status_code == 200
        and "Our standard API rate limit is 25 requests per day" in resp.text
    ):
        log.error(f"Rate limit reached: {resp.text}")
        return pd.DataFrame()

    if resp.status_code != 200:
        log.error(f"Server error: {resp.text}")
        return pd.DataFrame()

    data = resp.json()[f"Time Series ({interval}min)"]
    data_df = pd.DataFrame(data).T

    data_df.index = data_df.index.astype("datetime64[ns]")

    data_df = data_df.rename(columns={"4. close": "price"})
    data_df["price"] = data_df["price"].astype(float)
    data_df = data_df.reset_index().rename(columns={"index": "datetime"})

    data_df["price"] = data_df["price"].apply(lambda x: round(x, 2))
    data_df = data_df[["datetime", "price"]]
    return data_df.sort_values(
        "datetime",
        ascending=True,
    ).reset_index(drop=True)


def get_realtime_quote(ticker: str) -> dict[str, Any]:
    """
    Retrieves the real-time quote for a given ticker symbol.

    Args:
        ticker (str): The ticker symbol of the stock.

    Returns:
        dict[str, Any]: A dictionary containing the real-time quote information.
            - "datetime": The date and time of the quote.
            - "price": The current price of the stock.

    """
    finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
    quote = finnhub_client.quote(ticker.upper())
    return {
        "datetime": datetime.fromtimestamp(quote["t"]),
        "price": quote["c"],
    }


def calculate_signal_and_pnl(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates the signal, pnl and position for the DataFrame provided

    Args:
        df (DataFrame): pandas DataFrame with datetime, price, S_avg and sigma

    Returns:
        df (DataFrame): Return modified DataFrame with signal, pnl and position
    """
    df["signal"] = 0.0
    df["pnl"] = 0.0
    df["position"] = 0.0
    position = 0.0  # position is in dollar value, not number of shares
    for i in range(1, len(df) - 1):
        current_price = df.iloc[i]["price"]
        avg_price = df.iloc[i]["S_avg"]
        sigma = df.iloc[i]["sigma"]
        next_price = df.iloc[i + 1]["price"]

        if current_price > (avg_price + sigma):
            df.loc[i, "signal"] = 1
            position += next_price
            df.loc[i + 1, "position"] = position
        elif current_price < (avg_price - sigma):
            df.loc[i, "signal"] = -1
            position -= next_price
            df.loc[i + 1, "position"] = position
        else:
            df.loc[i, "signal"] = 0
            df.loc[i + 1, "position"] = position

    for i in range(1, len(df)):
        previous_position = df.iloc[i - 1]["position"]
        current_price = df.iloc[i]["price"]
        previous_price = df.iloc[i - 1]["price"]
        pnl = previous_position * ((current_price / previous_price) - 1)
        df.loc[i, "pnl"] = round(pnl, 2)

    return df


def calculate_avg_and_sigma(df, interval):
    """Calculates the rolling 24 hour avg price and sigma

    Args:
        df (DataFrame): pandas DataFrame wit datetime, price
        interval (int): Interval of time periods

    Returns:
        df (DataFrame): Return modified DataFrmae with avg price and sigma
    """
    window = 24 * 60 // interval
    df["S_avg"] = df["price"].rolling(window=window).mean().apply(lambda x: round(x, 2))
    df["sigma"] = df["price"].rolling(window=window).std()
    return df


def add_ticker(ticker, interval):
    """Gets historical data for ticker at given interval. Calculates S_avg, sigma, signal, pnl and position
    Saves data to {ticker}_price.csv and {ticker}_result.csv

    Args:
        ticker (str): Stock symbol
        interval (int): Interval of time period

    Returns:
        str or None: Return "Invalid ticker" or "server error". Returns None if everything is ok.
    """
    data_df = get_alpha_vantage_historical_data(ticker, interval=interval)
    if data_df.empty:
        return pd.DataFrame()

    data_df = calculate_avg_and_sigma(data_df, interval=interval)
    return calculate_signal_and_pnl(data_df)


def get_price(df, query_datetime) -> float | None:
    """Gets price for ticker at given query time

    Args:
        df (DataFrame): pandas DataFrame with datetime, price
        query_datetime (str): Datetime in YYYY-MM-DD-HH:MM format

    Returns:
        float or str: Returns price or No Data
    """
    price = df.loc[(df["datetime"] <= query_datetime)].tail(1)["price"].values
    if len(price) == 1:
        return price[0]
    return None


def get_signal(df, query_datetime) -> int | None:
    """Gets signal for ticker at given query time

    Args:
        df (DataFrame): pandas DataFrame with datetime, price
        query_datetime (str): Datetime in YYYY-MM-DD-HH:MM format

    Returns:
        int or str: Returns signal or No Data
    """
    signal = df.loc[(df["datetime"] <= query_datetime)].tail(1)["signal"].values
    if len(signal) == 1:
        return int(signal[0])
    return None


def save_report(data: dict[str, pd.DataFrame]):
    """Saves all tickers data to a single csv file named report.csv sorted by datetime and ticker

    Args:
        data (dict[str, pd.DataFrame]): A dictionary containing ticker data as pandas DataFrames.
            The keys represent the ticker symbols and the values represent the corresponding DataFrame.

    Returns:
        None
    """
    report_df = pd.DataFrame()
    for ticker in data:
        data_df = data[ticker][["datetime", "price", "signal", "pnl"]].copy()
        data_df["ticker"] = ticker
        data_df = data_df[["datetime", "ticker", "price", "signal", "pnl"]]

        report_df = pd.concat([report_df, data_df])

    report_df = report_df.sort_values(
        ["datetime", "ticker"],
        ascending=True,
    ).reset_index(drop=True)
    report_df.to_csv("data/report.csv", index=False)
