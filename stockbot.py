#!/usr/bin/env python
"""
StockBot

https://github.com/shirosaidev/stockbot

Copyright (C) Chris Park (shirosai) 2021
stockbot is released under the Apache 2.0 license. See
LICENSE for the full license text.
"""

import os, sys
import csv
import requests
import urllib.request
import time
import optparse
from requests import ReadTimeout, ConnectTimeout, HTTPError, Timeout, ConnectionError
from datetime import date, datetime, timedelta
from pytz import timezone
from random import randint
from urllib.parse import urlparse

from config import *

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError


STOCKBOT_VERSION = '0.1-b.3'
__version__ = STOCKBOT_VERSION

TZ = timezone('America/New_York')

APIKEYID = os.getenv('APCA_API_KEY_ID')
APISECRETKEY = os.getenv('APCA_API_SECRET_KEY')
APIBASEURL = os.getenv('APCA_API_BASE_URL')

api = tradeapi.REST(APIKEYID, APISECRETKEY, APIBASEURL)


def get_stock_info(stock):
    n = randint(1,2)
    url = "https://query{}.finance.yahoo.com/v8/finance/chart/{}?region=US&lang=en-US&includePrePost=false&interval=1d&range=1d&corsDomain=finance.yahoo.com&.tsrc=finance".format(n, stock)
    # stagger requests to avoid connection issues to yahoo finance
    time.sleep(randint(1, 3))
    headers = {
            'authority': 'query{}.finance.yahoo.com'.format(n), 
            'method': 'GET', 
            'scheme': 'https',
            'path': '/v8/finance/chart/{}?region=US&lang=en-US&includePrePost=false&interval=1d&range=1d&corsDomain=finance.yahoo.com&.tsrc=finance'.format(stock),
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-laguage': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'sec-fetch-dest': 'document',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-fetch-mode': 'navigate',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
            }
    try:
        r = requests.get(url, headers=headers)
    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError) as e:
        print('CONNECTION ERROR: {}'.format(e))
        time.sleep(randint(2, 5))
        get_stock_info(stock)
    stock_data = r.json()
    if stock_data['chart']['result'] is None:
        return None
    return stock_data


def get_stock_price(data):
    stock_price = data['chart']['result'][0]['meta']['regularMarketPrice']
    return stock_price


def get_closed_orders(startbuytime):
    if startbuytime == 'buyatclose':
        datestamp = date.today() - timedelta(days=1)
    else:
        datestamp = datetime.today().date()
    closed_orders = api.list_orders(
        status='closed',
        limit=100,
        after=datestamp
    )
    return closed_orders


def get_eod_change_percents(startbuytime):
    orders = get_closed_orders(startbuytime)
    todays_buy_sell = {}
    for order in orders:
        if order.symbol not in todays_buy_sell:
            todays_buy_sell[order.symbol] = {'buy': 0, 'sell': 0, 'change': 0}
        if order.side == 'sell':
            todays_buy_sell[order.symbol]['sell'] += int(order.filled_qty) * float(order.filled_avg_price)
        elif order.side == 'buy':
            todays_buy_sell[order.symbol]['buy'] += int(order.filled_qty) * float(order.filled_avg_price)
    for ticker in todays_buy_sell:
        todays_buy_sell[ticker]['change'] = round((todays_buy_sell[ticker]['sell'] - todays_buy_sell[ticker]['buy']) / 
                                            todays_buy_sell[ticker]['buy'] * 100, 2)
        todays_buy_sell[ticker]['sell'] = round(todays_buy_sell[ticker]['sell'], 2)
        todays_buy_sell[ticker]['buy'] = round(todays_buy_sell[ticker]['buy'], 2)
    return todays_buy_sell


def get_nasdaq_listed():
    nasdaqlist_url = "ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt"
    nasdaqlist_file = "nasdaqlisted.txt"
    if os.path.exists(nasdaqlist_file):
        age_in_sec = time.time() - os.path.getmtime(nasdaqlist_file)
        if age_in_sec > 604800:  # 1 week
            os.remove(nasdaqlist_file)
            urllib.request.urlretrieve(nasdaqlist_url, nasdaqlist_file)
    else:
        urllib.request.urlretrieve(nasdaqlist_url, nasdaqlist_file)
    nyse_tickers = []
    with open(nasdaqlist_file, 'r') as csvfile:
        filereader = csv.reader(csvfile, delimiter='|', quotechar='"')
        for row in filereader:
            nyse_tickers.append(row[0])
    del nyse_tickers[0]
    del nyse_tickers[-1]
    return nyse_tickers


def get_nasdaq_buystocks():
    # api used by https://www.nasdaq.com/market-activity/stocks/screener
    url = NASDAQ_API_URL
    parsed_uri = urlparse(url)
    # stagger requests to avoid connection issues to nasdaq.com
    time.sleep(randint(1, 3))
    headers = {
        'authority': parsed_uri.netloc, 
        'method': 'GET', 
        'scheme': 'https',
        'path': parsed_uri.path + '?' + parsed_uri.params,
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'accept-laguage': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-fetch-dest': 'document',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'
        }
    try:
        r = requests.get(url, headers=headers)
    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError) as e:
        print('CONNECTION ERROR: {}'.format(e))
        time.sleep(randint(2, 5))
        get_nasdaq_buystocks()
    return r.json()


def alpaca_order(symbol, side, _type='market', time_in_force='day'):
    try:
        api.submit_order(
            symbol=symbol,
            qty=NUM_SHARES,
            side=side,
            type=_type,
            time_in_force=time_in_force
        )
    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError, APIError) as e:
        print('CONNECTION ERROR: {}'.format(e))
        time.sleep(randint(1, 3))
        alpaca_order(symbol, side)


def main():
    usage = """Usage: stockbot.py [-h] [-t tradealgo] [-b startbuytime]

StockBot v{0}
Alpaca algo stock trading bot.""".format(STOCKBOT_VERSION)
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-t', '--tradealgo', default='moved', 
                        help='algo to use for trading, options are moved, lowtomarket or lowtohigh, default "%default"')
    parser.add_option('-b', '--startbuytime', default='buyatopen', 
                        help='when to starting buying stocks, options are buyatopen, and buyatclose, default "%default"')
    options, args = parser.parse_args()
    
    # print banner
    banner = """\033[32m                                
    _____ _           _   _____     _   
    |   __| |_ ___ ___| |_| __  |___| |_ 
    |__   |  _| . |  _| '_| __ -| . |  _|
    |_____|_| |___|___|_,_|_____|___|_|  
    StockBot v{0}    +$ = :)  -$ = ;(\n
    https://github.com/shirosaidev/stockbot\033[0m\n\n""".format(STOCKBOT_VERSION)

    print(banner)
    
    tradealgo = options.tradealgo
    startbuytime = options.startbuytime

    print('Trade algo: {}'.format(tradealgo))
    print('Buy time: {}'.format(startbuytime))

    # Get our account information.
    account = api.get_account()
    
    print('Account info:')
    print(account)

    # Check if our account is restricted from trading.
    if account.trading_blocked:
        print('Account is currently restricted from trading.')
        sys.exit(0)
        
    # List current positions
    print('Current positions:')
    print(api.list_positions())

    equity = START_EQUITY

    # times to buy/sell

    if startbuytime == 'buyatopen':
        get_stocks_h, get_stocks_m = BAO_GET_STOCKS_TIME.split(':')
        buy_sh, buy_sm = BAO_BUY_START_TIME.split(':')
        buy_eh, buy_em = BAO_BUY_END_TIME.split(':')
        sell_sh, sell_sm = BAO_SELL_START_TIME.split(':')
        sell_eh, sell_em = BAO_SELL_END_TIME.split(':')
    else:  # buy at close
        get_stocks_h, get_stocks_m = BAC_GET_STOCKS_TIME.split(':')
        buy_sh, buy_sm = BAC_BUY_START_TIME.split(':')
        buy_eh, buy_em = BAC_BUY_END_TIME.split(':')
        sell_sh, sell_sm = BAC_SELL_START_TIME.split(':')
        sell_eh, sell_em = BAC_SELL_END_TIME.split(':')

    while True:
        try:
            # get the best buy and strong buy stock from Nasdaq.com and 
            # sort them by the best stocks using one of the chosen algo

            if datetime.today().weekday() in BUY_DAYS and datetime.now(tz=TZ).hour == get_stocks_h \
                and datetime.now(tz=TZ).minute == get_stocks_m:

                print(datetime.now(tz=TZ).isoformat())
                print('getting buy and strong buy stocks from Nasdaq.com...')

                stock_info = []

                data = get_nasdaq_buystocks()

                strong_buy_stocks = []

                for d in data['data']['table']['rows']:
                    # Get daily price data for stock symbol over the last n trading days.
                    barset = api.get_barset(d['symbol'], 'day', limit=MOVED_DAYS)
                    if not barset[d['symbol']]:
                        print('stock symbol {} not found'.format(d['symbol']))
                        continue
                    stock_bars = barset[d['symbol']]

                    # See how much stock ticker moved in that timeframe.
                    if MOVED_DAYS_CALC == 0:
                        price_open = stock_bars[0].o
                        price_close = stock_bars[-1].c
                        percent_change = round((price_close - price_open) / price_open * 100, 3)
                    else:
                        prices = []
                        x = 0
                        while x < MOVED_DAYS:
                            price_open = stock_bars[x].o
                            price_close = stock_bars[x].c
                            percent_change = round((price_close - price_open) / price_open * 100, 3)
                            prices.append(percent_change)
                            x += 1
                        avg = round(sum(prices) / MOVED_DAYS, 3)
                        percent_change = avg
                        
                    print('{} moved {}% over the last {} days'.format(d['symbol'], percent_change, MOVED_DAYS))
                    
                    strong_buy_stocks.append({'symbol': d['symbol'], 'company': d['name'], 
                                                'moved': percent_change})

                for stock_item in strong_buy_stocks:
                    stock = stock_item['symbol']
                    #print('DEBUG', stock)
                    sys.stdout.write('.')
                    sys.stdout.flush()

                    data = get_stock_info(stock)
                    if not data:
                        print('stock symbol {} not found in yahoo finance'.format(stock))
                        continue
                    # check which market it's in
                    exchange_name = data['chart']['result'][0]['meta']['exchangeName']
                    if exchange_name not in ['NYQ', 'NMS']:
                        print('stock symbol {} in different exchange {}'.format(stock, exchange_name))
                        continue

                    try:
                        stock_high = round(data['chart']['result'][0]['indicators']['quote'][0]['high'][1], 2)
                    except Exception:
                        stock_high = round(data['chart']['result'][0]['indicators']['quote'][0]['high'][0], 2)

                    try:
                        stock_low = round(data['chart']['result'][0]['indicators']['quote'][0]['low'][1], 2)
                    except Exception:
                        stock_low = round(data['chart']['result'][0]['indicators']['quote'][0]['low'][0], 2)

                    change_low_to_high = round(stock_high - stock_low, 3)

                    stock_price = get_stock_price(data)

                    try:
                        stock_volume = data['chart']['result'][0]['indicators']['quote'][0]['volume'][1]
                    except Exception:
                        stock_volume = data['chart']['result'][0]['indicators']['quote'][0]['volume'][0]

                    if stock_price > STOCK_MAX_PRICE or stock_price < STOCK_MIN_PRICE:
                        continue

                    change_low_to_market = round(stock_price - stock_low, 3)

                    stock_info.append({'symbol': stock, 'company': stock_item['company'], 
                                        'market_price': stock_price, 'low': stock_low, 
                                        'high': stock_high, 'volume': stock_volume,
                                        'change_low_to_high': change_low_to_high,
                                        'change_low_to_market': change_low_to_market,
                                        'moved': stock_item['moved']})
                
                # sort stocks
                if tradealgo == 'moved':
                    biggest_movers = sorted(stock_info, key = lambda i: i['moved'], reverse = True)
                elif tradealgo == 'lowtomarket':
                    biggest_movers = sorted(stock_info, key = lambda i: i['change_low_to_market'], reverse = True)
                elif tradealgo == 'lowtohigh':
                    biggest_movers = sorted(stock_info, key = lambda i: i['change_low_to_high'], reverse = True)

                stock_picks = biggest_movers[0:MAX_NUM_STOCKS]
                print('\n')

                print(datetime.now(tz=TZ).isoformat())
                print('today\'s stocks {}'.format(stock_info))
                print('\n')
                print('today\'s picks {}'.format(stock_picks))
                print('\n')


            # buy stocks

            # buy at open
            # check stock prices at 9:30am EST (market open) and continue to check for the next 1.5 hours
            # to see if stock is going down or going up, when the stock starts to go up, buy

            # buy at close
            # buy stocks at 3:00pm EST and hold until next day

            if datetime.today().weekday() in [0,1,2,3,4] and datetime.now(tz=TZ).hour == buy_sh \
                and datetime.now(tz=TZ).minute == buy_sm:

                print(datetime.now(tz=TZ).isoformat())
                print('starting to buy stocks...')

                stock_prices = []
                stock_bought_prices = []
                bought_stocks = []

                total_buy_price = 0
                while True:
                    for stock in stock_picks:
                        already_bought = False
                        for stockval in stock_bought_prices:
                            if stockval[0] == stock['symbol']:
                                already_bought = True
                                break
                        if already_bought:
                            continue

                        data = get_stock_info(stock['symbol'])
                        stock_price_buy = get_stock_price(data)

                        # count the number of stock prices for the stock we have
                        num_prices = 0
                        went_up = 0
                        went_down = 0
                        for stockitem in stock_prices:
                            if stockitem[0] == stock['symbol']:
                                num_prices +=1
                                # check prev. price compared to now to see if it went up or down
                                if stock_price_buy > stockitem[1]:
                                    went_up += 1
                                else:
                                    went_down += 1

                        # buy the stock if there are 5 records of it and it's gone up and if we have
                        # enough equity left to buy
                        # if buying at end of day, ignore record checking to force it to buy

                        if startbuytime == 'buyatclose':
                            n = 0
                            went_up = 1
                            went_down = 0
                        else:
                            n = 5
                        buy_price = stock_price_buy * NUM_SHARES
                        if num_prices >= n and went_up > went_down and equity >= buy_price:
                            buy_time = datetime.now(tz=TZ).isoformat()
                            print(buy_time)
                            alpaca_order(stock['symbol'], side='buy')
                            print('placed buy order of stock {} ({}) for ${} (vol {})'.format(
                                stock['symbol'], stock['company'], stock_price_buy, stock['volume']))
                            total_buy_price += buy_price
                            stock_bought_prices.append([stock['symbol'], stock_price_buy, buy_time])
                            bought_stocks.append(stock)
                            equity -= buy_price
                        
                        stock_prices.append([stock['symbol'], stock_price_buy])

                    # sleep and check prices again after 2 min if time is before 11:00am EST / 4:00pm EST (market close)
                    if len(stock_bought_prices) == MAX_NUM_STOCKS or \
                        equity == 0 or \
                        (datetime.now(tz=TZ).hour == buy_eh and datetime.now(tz=TZ).minute >= buy_em):
                        break
                    else:
                        time.sleep(120)
                
                print(datetime.now(tz=TZ).isoformat())
                print('sent buy orders for {} stocks, market price ${}'.format(len(bought_stocks), round(total_buy_price, 2)))
                if startbuytime == 'buyatclose':
                    print('holding these stocks and selling them the next market open day...')
                print('\n')

            # sell stocks

            # check stock prices at 9:30am EST (buy at close) / 11:00am EST and continue to check until 1:00pm EST to
            # see if it goes up by x percent, sell it if it does
            # when the stock starts to go down starting at 1:00pm EST, sell or 
            # sell at end of day 2:00pm EST (buy at close) / 3:30pm EST
            
            if datetime.today().weekday() in [0,1,2,3,4] and datetime.now(tz=TZ).hour == sell_sh \
                and datetime.now(tz=TZ).minute >= sell_sm:

                stock_prices = []

                stock_sold_prices = []

                stock_data_csv = [['symbol', 'company', 'buy', 'buy time', 'sell', 'sell time', 'profit', 'percent', 'vol sod', 'vol sell']]

                print(datetime.now(tz=TZ).isoformat())
                print('selling stock if it goes up by {}%...'.format(SELL_PERCENT_GAIN))

                while True:
                    for stock in bought_stocks:
                        already_sold = False
                        for stockval in stock_sold_prices:
                            if stockval[0] == stock['symbol']:
                                already_sold = True
                                break
                        if already_sold:
                            continue

                        data = get_stock_info(stock['symbol'])
                        stock_price_sell = get_stock_price(data)

                        stockinfo = [ x for x in stock_bought_prices if x[0] is stock['symbol'] ]
                        stock_price_buy = stockinfo[0][1]
                        buy_time = stockinfo[0][2]

                        # sell the stock if it's gone up by x percent
                        change_perc = round((stock_price_sell - stock_price_buy) / stock_price_buy * 100, 2)
                        sell_time = datetime.now(tz=TZ).isoformat()
                        diff = round(stock_price_sell - stock_price_buy, 2)
                        if change_perc >= SELL_PERCENT_GAIN:
                            print(sell_time)
                            alpaca_order(stock['symbol'], side='sell')
                            stock_data = get_stock_info(stock['symbol'])
                            stock_vol_now = stock_data['chart']['result'][0]['indicators']['quote'][0]['volume'][0]
                            print('placed sell order of stock {} ({}) for ${} (diff ${} {}%) (vol {})'.format(
                                stock['symbol'], stock['company'], stock_price_sell, diff, change_perc, stock_vol_now))
                            sell_price = stock_price_sell * NUM_SHARES
                            stock_data = get_stock_info(stock['symbol'])
                            stock_vol_now = stock_data['chart']['result'][0]['indicators']['quote'][0]['volume'][0]
                            stock_data_csv.append([stock['symbol'], stock['company'], stock_price_buy, buy_time, 
                                                    stock_price_sell, sell_time, diff, change_perc, stock['volume'], stock_vol_now])
                            stock_sold_prices.append([stock['symbol'], stock_price_sell, sell_time])
                            equity += sell_price
                        else:
                            print(sell_time)
                            print('stock {} ({}) hasn\'t gone up enough to sell ${} (diff ${} {}%)'.format(
                                stock['symbol'], stock['company'], stock_price_sell, diff, change_perc))

                    # sleep and check prices again after 2 min if time is before 1:00pm EST
                    if len(stock_sold_prices) == len(bought_stocks) or \
                        (datetime.now(tz=TZ).hour == 13 and datetime.now(tz=TZ).minute >= 0):  # 1:00pm EST
                        break
                    else:
                        time.sleep(120)

                if len(stock_sold_prices) < len(bought_stocks) and \
                    (datetime.now(tz=TZ).hour == 13 and datetime.now(tz=TZ).minute >= 0):  # 1:00pm EST
                
                    print(datetime.now(tz=TZ).isoformat())
                    print('selling any remaining stocks if they go down, or else sell at end of day...')

                    while True:
                        for stock in bought_stocks:
                            already_sold = False
                            for stockval in stock_sold_prices:
                                if stockval[0] == stock['symbol']:
                                    already_sold = True
                                    break
                            if already_sold:
                                continue

                            data = get_stock_info(stock['symbol'])
                            stock_price_sell = get_stock_price(data)

                            # count the number of stock prices for the stock we have
                            num_prices = 0
                            went_up = 0
                            went_down = 0
                            for stockitem in stock_prices:
                                if stockitem[0] == stock['symbol']:
                                    num_prices +=1
                                    # check prev. price compared to now to see if it went up or down
                                    if stock_price_sell > stockitem[1]:
                                        went_up += 1
                                    else:
                                        went_down += 1

                            stock_prices.append([stock['symbol'], stock_price_sell])

                            # sell the stock if there are 15 records of it and it's gone down
                            # or sell if it's the end of the day
                            if (num_prices >= 15 and went_down > went_up) or (datetime.now(tz=TZ).hour == sell_eh \
                                and datetime.now(tz=TZ).minute >= sell_em):
                                stockinfo = [ x for x in stock_bought_prices if x[0] is stock['symbol'] ]
                                stock_price_buy = stockinfo[0][1]
                                buy_time = stockinfo[0][2]
                                diff = round(stock_price_sell - stock_price_buy, 2)
                                change_perc = round((stock_price_sell - stock_price_buy) / stock_price_buy * 100, 2)
                                sell_time = datetime.now(tz=TZ).isoformat()
                                print(sell_time)
                                alpaca_order(stock['symbol'], side='sell')
                                stock_data = get_stock_info(stock['symbol'])
                                stock_vol_now = stock_data['chart']['result'][0]['indicators']['quote'][0]['volume'][0]
                                print('placed sell order of stock {} ({}) for ${} (diff ${} {}%) (vol {})'.format(
                                    stock['symbol'], stock['company'], stock_price_sell, diff, change_perc, stock_vol_now))
                                sell_price = stock_price_sell * NUM_SHARES
                                stock_data_csv.append([stock['symbol'], stock['company'], stock_price_buy, buy_time, 
                                                        stock_price_sell, sell_time, diff, change_perc, stock['volume'], stock_vol_now])
                                stock_sold_prices.append([stock['symbol'], stock_price_sell, sell_time])
                                equity += sell_price

                        # sleep and check prices again after 2 min if time is before # 3:30pm EST / 2:30pm EST (buy at close)
                        if len(stock_sold_prices) == len(bought_stocks) or \
                            (datetime.now(tz=TZ).hour == sell_eh and datetime.now(tz=TZ).minute >= sell_em):
                            break
                        time.sleep(120)

                    # sold all stocks or market close

                    percent = round((equity - START_EQUITY) / START_EQUITY * 100, 2)
                    equity = round(equity, 2)
                    print(datetime.now(tz=TZ).isoformat())
                    print('*** PERCENT {}%'.format(percent))
                    print('*** EQUITY ${}'.format(equity))

                    # wait until end of day for all the final sells and
                    # print an Alpaca stock summary
                    print('waiting for Alpaca report...')
                    while True:
                        if datetime.now(tz=TZ).hour == sell_eh and datetime.now(tz=TZ).minute >= sell_em + 5:
                            break
                        time.sleep(60)

                    # print out summary of today's buy/sells on alpaca

                    todays_buy_sell = get_eod_change_percents(startbuytime)
                    print(datetime.now(tz=TZ).isoformat())
                    print(todays_buy_sell) 
                    print('********************')
                    print('TODAY\'S PROFIT/LOSS')
                    print('********************')
                    total_profit = 0
                    total_buy = 0
                    total_sell = 0
                    n = 0
                    stock_data_csv.append([])
                    stock_data_csv.append(['symbol', 'buy', 'sell', 'change'])
                    for k, v in todays_buy_sell.items():
                        change_str = '{}{}'.format('+' if v['change']>0 else '', v['change'])
                        print('{} {}%'.format(k, change_str))
                        stock_data_csv.append([k, v['buy'], v['sell'], v['change']])
                        total_profit += v['change']
                        total_buy += v['buy']
                        total_sell += v['sell']
                        n += 1
                    print('-------------------')
                    sum_str = '{}{}%'.format('+' if v['change']>0 else '', round(total_profit, 2))
                    avg_str = '{}{}%'.format('+' if v['change']>0 else '', round(total_profit/n, 2))
                    buy_str = '${}'.format(round(total_buy, 2))
                    sell_str = '${}'.format(round(total_sell, 2))
                    profit_str = '${}'.format(round(total_sell - total_buy, 2))
                    print('*** SUM {}'.format(sum_str))
                    print('*** AVG {}'.format(avg_str))
                    print('*** BUY {}'.format(buy_str))
                    print('*** SELL {}'.format(sell_str))
                    print('*** PROFIT/LOSS {}'.format(profit_str))

                    # write csv

                    now = datetime.now(tz=TZ).date().isoformat()
                    csv_file = 'stocks_{0}_{1}.csv'.format(tradealgo, now)
                    f = open(csv_file, 'w')

                    with f:
                        writer = csv.writer(f)
                        for row in stock_data_csv:
                            writer.writerow(row)
                        writer.writerow([])
                        writer.writerow(["PERCENT", percent])
                        writer.writerow(["EQUITY", equity])
                        writer.writerow([])
                        writer.writerow(["SUM", sum_str])
                        writer.writerow(["AVG", avg_str])
                        writer.writerow([])
                        writer.writerow(["BUY", buy_str])
                        writer.writerow(["SELL", sell_str])
                    
                    # set equity back to start value to not reinvest any gains
                    if equity > START_EQUITY:
                        equity = START_EQUITY

            print(datetime.now(tz=TZ).isoformat(), '$ zzz...')
            time.sleep(60)

        except KeyboardInterrupt:
            print('Ctrl+c pressed, exiting')

if __name__ == "__main__":
    main()