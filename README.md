# stockbot
Alpaca algo stock trading bot

[![License](https://img.shields.io/github/license/shirosaidev/stockbot.svg?label=License&maxAge=86400)](./LICENSE)
[![Release](https://img.shields.io/github/release/shirosaidev/stockbot.svg?label=Release&maxAge=60)](https://github.com/shirosaidev/stockbot/releases/latest)
[![Sponsor Patreon](https://img.shields.io/badge/Sponsor%20%24-Patreon-brightgreen.svg)](https://www.patreon.com/shirosaidev)
[![Donate PayPal](https://img.shields.io/badge/Donate%20%24-PayPal-brightgreen.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=CLF223XAS4W72)

Get recommended buy and strong buy stocks daily from Nasdaq.com and get prices from Yahoo and determine which stocks moved the most the previous n days, sort those by largest movers (based on open/close $) and buy those stocks if they are going up. When the stock price goes up enough, or at the end of the market day, sell any purchased stocks.


## Options

Trade algo can be set to:

"moved" - uses which stock moved the most in past n days (n days set in config) (default) 

"lowtomarket" - uses low price to market price

"lowtohigh" - uses low price to high price

Buy time can bet set to:

"buyatopen" - buy the stocks when market opens and sell when price increases enough or at end of day, whatever comes first

"buyatclose" - buy the stocks before market closes, and hold until next day, if stock price goes up enough sell, or sell at end of next market day

## Slack workspace
Join the conversation, get support, etc on [stocksight Slack](https://join.slack.com/t/stocksightworkspace/shared_invite/enQtNzk1ODI0NjA3MTM4LTA3ZDA0YzllOGNiM2I5ZjAzYWM2MjNmMjI0OTRlY2ZjYTk1NmM5YmEwMmMwOTE2OTNiMGZlNzdjZmZkM2RjM2U).

## Requirements

Uses Alpaca https://alpaca.markets/ for trading. You will need an account with Alpaca to use stockbot.

Set env vars for Alpaca authentication api keys:

```sh
export APCA_API_KEY_ID=<key_id>
export APCA_API_SECRET_KEY=<secrect_key>
export APCA_API_BASE_URL=url
```

url set to:

https://api.alpaca.markets (for live)

https://paper-api.alpaca.markets (for paper)


Install requirements Alpaca python library:

```sh
pip3 install -r requirements.txt
```

### Download

```shell
$ git clone https://github.com/shirosaidev/stockbot.git
$ cd stockbot
```
[Download latest version](https://github.com/shirosaidev/stockbot/releases/latest)

## How to use

Copy sample config:

```sh
cp config.py.sample config.py
```

Edit config.py and adjust settings as needed.

Run stockbot:

```sh
python3 stockbot.py -t <tradealgo> -b <buytime>
```

Stockbot runs in an infinite loop and does daily trading. To stop it, press ctrl+c. Stocks will manually have to be sold on Alpaca web site since stockbot does not keep track of stocks when you exit it.


## Disclaimer

This software is for educational purposes only. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS. Do not risk money which you are afraid to lose. There might be bugs in the code - this software DOES NOT come with ANY warranty.
