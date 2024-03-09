import argparse
import atexit
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask
from flask_restful import Api, Resource
from logger import log
from utils import (
    add_ticker,
    calculate_avg_and_sigma,
    calculate_signal_and_pnl,
    get_price,
    get_realtime_quote,
    get_signal,
    save_report,
)
from waitress import serve

# Create Data and logs folder if they don't already exist
if not Path("data/").exists():
    Path("data/").mkdir()
if not Path("logs/").exists():
    Path("logs/").mkdir()


# Classes for Flask-restful routes/endpoints
class HomePage(Resource):
    def get(self):
        return "Connected to trading server"


class Data(Resource):
    def get(self, query_time: str):
        """
        Retrieves the price and signal for each ticker at the specified query time.

        Args:
            query_time (str): The query time in the format "%Y-%m-%d-%H:%M".

        Returns:
            dict: A dictionary containing the ticker as the key and a dictionary with the price and signal as the value.
        """

        query_datetime: datetime = datetime.strptime(query_time, "%Y-%m-%d-%H:%M")

        updated_data = get_latest_data()

        result: dict[str, dict[str, Any]] = {}

        for ticker in updated_data:
            result[ticker] = {
                "price": get_price(updated_data[ticker], query_datetime),
                "signal": get_signal(updated_data[ticker], query_datetime),
            }
        return result


class Report(Resource):
    def get(self):
        """Recreate report.csv with latest price, signal and pnl for each ticker"""

        updated_data = get_latest_data()
        save_report(updated_data)
        return "report.csv updated with latest data"


class DeleteTicker(Resource):
    def delete(self, ticker):
        ticker = ticker.upper()
        if ticker in data:
            del data[ticker]
            return f"Deleted {ticker} from server data"
        return f"{ticker} not in server data", 404


class AddTicker(Resource):
    def post(self, ticker):
        ticker = ticker.upper()
        if ticker in data:
            return f"{ticker} already in server data", 208

        data[ticker] = add_ticker(ticker, args.minutes)
        if not data[ticker].empty:
            return f"Added {ticker} to server data"

        del data[ticker]
        return f"Error adding {ticker} to server data", 400


def get_latest_data():
    """Function to get realtime data from Finnhub for every symbol and append to existing dataframe.
    Returns None
    """
    result = {}
    for ticker in data:
        log.info("Getting realtime data for: %s", ticker)
        try:
            realtime_quote = get_realtime_quote(ticker)
        except Exception as e:
            log.exception(f"Error getting realtime data for {ticker}: {e}")
            continue
        data_df = data[ticker].copy()

        # appends realtime quote to existing interal data structure
        data_df.loc[data_df.shape[0], ("datetime", "price")] = (
            realtime_quote["datetime"],
            realtime_quote["price"],
        )
        data_df["datetime"] = pd.to_datetime(data_df["datetime"])
        data_df = calculate_avg_and_sigma(data_df, interval=args.minutes)
        data_df = calculate_signal_and_pnl(data_df)
        result[ticker] = data_df

    return result


def main(port: int):
    """Creates and runs Flask app through waitress.
    Runs a loop on a separate thread to continously update data every X minutes after server startup
    """

    app = Flask(__name__)

    api = Api(app)
    api.add_resource(HomePage, "/")
    api.add_resource(Data, "/data/<query_time>")
    api.add_resource(AddTicker, "/add_ticker/<ticker>")
    api.add_resource(DeleteTicker, "/del_ticker/<ticker>")
    api.add_resource(Report, "/report")

    log.info("Trading server started...accepting requests from client")
    serve(app, listen=f"*:{args.port}")


def server_start_up_tasks(tickers: list[str]):
    """Startup tasks to run when the server starts.
    Tasks:
    - add historical data from list of tickers provided
    - computes 24 hour rolling moving avg and sigma for each ticker
    - computes signal and pnl for each ticker
    """
    for ticker in tickers:
        data[ticker] = add_ticker(
            ticker=ticker,
            interval=args.minutes,
        )

    save_report(data)

    log.info("Server startup tasks completed")


def at_keyboard_interrupt():
    sys.exit(0)


atexit.register(at_keyboard_interrupt)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process arguments when server starts")

    parser.add_argument(
        "-t",
        "--tickers",
        nargs="+",
        default=["AAPL"],
        help="If specified, download data for all the US tickers specified. If this option is not specified, the server will download data for ticker 'AAPL'",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="It specifies the network port for the server. This argument is optional, and default port is 8000.",
    )
    parser.add_argument(
        "-m",
        "--minutes",
        type=int,
        default=5,
        choices=[5, 15, 30, 60],
        help="It specifies the sample data being downloaded. It only accepts (5,15,30,60) as inputs, and default value is 5.",
    )
    # parses initial arguments
    args = parser.parse_args()
    log.info(args)

    args.tickers = [ticker.upper() for ticker in args.tickers]

    try:
        data: dict[str, pd.DataFrame] = {}
        server_start_up_tasks(args.tickers)
        main(args.port)
    except KeyboardInterrupt:
        log.exception("Server Terminated")
        sys.exit(0)
