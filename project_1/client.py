import argparse
import re
from datetime import datetime
from typing import Any

import requests
from logger import log

parser = argparse.ArgumentParser(description="Process client command line arguments")

parser.add_argument(
    "-sa",
    "--server_address",
    type=str,
    default="127.0.0.1:8000",
    help="If specified, connect to server running on the IP address, and use specified port number. If this option is not specified, client assumes that the server is running on 127.0.0.1:8000",
)


def get_base_url(ip_address="127.0.0.1", port=8000):
    """Creates base url with default ip address and port

    Args:
        ip_address (str, optional): Ip address to connect to. Defaults to "127.0.0.1".
        port (int, optional): Port to connect to . Defaults to 8000.

    Returns:
        str: Base url
    """
    return f"http://{ip_address}:{port}"


def is_valid_server_address(server_address):
    """Checks whether the provided server address is valid or not.

    Args:
        server_address (str): server_address

    Returns:
        bool: Bool to indicate whether server_address is valid or not
    """
    is_valid = re.fullmatch(
        r"^\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}:\d{1,5}$",
        server_address,
    )
    return bool(is_valid)


def main():
    """Main function to run the client"""
    log.info("Running client")

    while True:
        input_command = input("Enter command: ")
        if input_command == "exit":
            log.info("Exiting client")
            break

        if input_command == "report":
            r = requests.get(url=base_url + "/report", timeout=30)
            if r.status_code == 200:
                log.info(r.json())
            else:
                log.info(r.json())
            continue

        command, arg = input_command.split(" ")
        if command == "add":
            r = requests.post(url=base_url + f"/add_ticker/{arg}", timeout=30)
            if r.status_code == 200:
                log.info(f"Added ticker {arg}")
            elif r.status_code == 208:
                log.info(f"Ticker {arg} already in server data")
            else:
                log.error(f"Error adding ticker {arg} to server data")
            continue

        if command == "delete":
            r = requests.delete(url=base_url + f"/del_ticker/{arg}", timeout=30)
            if r.status_code == 200:
                log.info(f"Deleted ticker {arg}")
            elif r.status_code == 404:
                log.info(f"{arg} not in server data")
            continue

        if command == "data":
            r = requests.get(url=base_url + f"/data/{arg}", timeout=30)
            if r.status_code == 200:
                data: dict[str, dict[str, Any]] = r.json()
                for ticker in data:
                    log.info(
                        f"{ticker}   {data[ticker]['price']}, {data[ticker]['signal']}",
                    )
            else:
                log.error("Server error, unable to get the latest price and signal")


if __name__ == "__main__":
    args = parser.parse_args()
    log.info(args)
    base_url = get_base_url()
    if args.server_address and is_valid_server_address(args.server_address):
        ip_address, port = args.server_address.split(":")
        base_url = get_base_url(ip_address=ip_address, port=port)
        r = requests.get(url=base_url + "/", timeout=15)
        if r.status_code == 200:
            log.info(f"Connected to trading server at {base_url}")
    else:
        log.info("Invalid server address")
    main()
