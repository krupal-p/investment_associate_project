# Investment Associate Project

## Project 1

### Installation

`pip install -r requirements.txt`

### Usage

#### Starting the server

`cd project_1`

`python server.py --tickers AAPL MSFT GOOGL --port 7000`

#### Starting the client

`python client.py --server <ip>:<port>`

Once the client is running, you can type in the following commands:

`data YYYY-MM-DD-HH:MM`

Client will query the server for latest price and signal available as of the time specified. If a future date is specified, it'll return the latest price and signal available.

`delete TICKER`

Instruct the server to delete a ticker from the server data set.

`add TICKER`

Instruct the server to add a new ticker to the server data set.

`report`

Instruct the server to recreate report.csv with latest data, signal, pnl. Report can be found under project_1/data folder.

`exit`

Exit the client.

API Keys for Alpha Vantage and FINHUB can be specified in the config.txt file.

## Project 2

Analysis of the data can be found in the notebook under project_2 folder.
