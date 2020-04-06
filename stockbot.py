#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""stockbot.py - get recommended buy and strong buy stocks
daily from Nasdaq.com and get prices from Yahoo and determine
which stocks moved the most the previous day, sort those by 
largest movers (based on open/close $) and buy those stocks
if they are going up. At the end of the market day, sell 
any purchased stocks.

Copyright (C) Chris Park 2020. All rights reserved.
"""

import os, sys
import csv
import requests
from requests import ReadTimeout, ConnectTimeout, HTTPError, Timeout, ConnectionError
import urllib.request
import csv
import time
from datetime import datetime
from pytz import timezone
from random import randint
import collections
import alpaca_trade_api as tradeapi


STOCKBOT_VERSION = '0.1-b.1'
__version__ = STOCKBOT_VERSION

TZ = timezone('America/New_York')

api = tradeapi.REST('PKJUK5SQ6REUFTCV7QJC', 'dsm/Ywauqgx8YUEZJXa/lNREMds6fly745P3FT13', 'https://paper-api.alpaca.markets')

STOCK_MAX_PRICE = 100
STOCK_MIN_PRICE = 20
MAX_NUM_STOCKS = 20
NUM_SHARES = 5
SELL_PERCENT_GAIN = 3

START_EQUITY = 5000


def get_stock_info(stock):
    n = randint(1, 2)
    url = "https://query{0}.finance.yahoo.com/v8/finance/chart/{1}?region=US&lang=en-US&includePrePost=false&interval=1d&range=1d&corsDomain=finance.yahoo.com&.tsrc=finance".format(n, stock)
    try:
        # stagger requests to avoid connection issues to yahoo finance
        time.sleep(randint(1, 2))
        r = requests.get(url)
    except (ConnectTimeout, HTTPError, ReadTimeout, Timeout, ConnectionError) as e:
        print('CONNECTION ERROR: {}'.format(e))
        time.sleep(randint(2, 3))
        get_stock_info(stock)
    stock_data = r.json()
    #print('DEBUG', stock_data)
    if stock_data['chart']['result'] is None:
        return None
    return stock_data


def get_stock_price(data):
    stock_price = data['chart']['result'][0]['meta']['regularMarketPrice']
    return stock_price


def get_closed_orders():
    closed_orders = api.list_orders(
        status='closed',
        limit=100,
        after=datetime.today().date()
    )
    return closed_orders


def get_eod_change_percents():
    orders = get_closed_orders()
    todays_buy_sell = {}
    for order in orders:
        if order.symbol not in todays_buy_sell:
            todays_buy_sell[order.symbol] = {'buy': 0, 'sell': 0, 'change': 0}
        if order.side == 'sell':
            todays_buy_sell[order.symbol]['sell'] += round(int(order.filled_qty) * float(order.filled_avg_price), 2)
        elif order.side == 'buy':
            todays_buy_sell[order.symbol]['buy'] += round(int(order.filled_qty) * float(order.filled_avg_price), 2)
    for ticker in todays_buy_sell:
        todays_buy_sell[ticker]['change'] = round((todays_buy_sell[ticker]['sell'] - todays_buy_sell[ticker]['buy']) / 
                                            todays_buy_sell[ticker]['buy'] * 100, 2)
    return todays_buy_sell


def get_nyse_tickers():
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


def main():
    # print banner
    banner = """\033[32m                                
    _____ _           _   _____     _   
    |   __| |_ ___ ___| |_| __  |___| |_ 
    |__   |  _| . |  _| '_| __ -| . |  _|
    |_____|_| |___|___|_,_|_____|___|_|  
    StockBot v{0}    +$ = :)  -$ = ;(\033[0m\n""".format(STOCKBOT_VERSION)

    print(banner)
    try:
        tradealgo = sys.argv[1]
        if tradealgo not in ['rating', 'lowtomarket', 'moved']:
            print('required arg missing, use rating, lowtomarket, or moved')
            sys.exit(1)
    except IndexError:
        print('required arg missing, use rating, lowtomarket, or moved')
        sys.exit(0)
    print('Trade algo: {}'.format(tradealgo))

    # Get our account information.
    account = api.get_account()

    # Check if our account is restricted from trading.
    if account.trading_blocked:
        print('Account is currently restricted from trading.')
        sys.exit(0)

    equity = START_EQUITY

    while True:

        # get the best rated buy and strong buy stock from Nasdaq.com and sort them by the best movers the prev day
        if datetime.today().weekday() in [0,1,2,3,4] and datetime.now(tz=TZ).hour == 8 \
            and datetime.now(tz=TZ).minute == 0:  # 8:00am EST

            print(datetime.now(tz=TZ).isoformat())
            print('getting buy and strong buy stocks from Nasdaq.com...')

            stock_info = []

            url = "https://www.nasdaq.com/api/v1/screener?marketCap=Large,Medium,Small&analystConsensus=StrongBuy,Buy&page=1&pageSize=100"

            r = requests.get(url)
            data = r.json()

            strong_buy_stocks = []

            for d in data['data']:
                # Get daily price data for stock ticker over the last 5 trading days.
                barset = api.get_barset(d['ticker'], 'day', limit=5)
                if not barset[d['ticker']]:
                    print('stock ticker {} not found'.format(d['ticker']))
                    continue
                stock_bars = barset[d['ticker']]

                # See how much stock ticker moved in that timeframe.
                week_open = stock_bars[0].o
                week_close = stock_bars[-1].c
                percent_change = round((week_close - week_open) / week_open * 100, 3)

                print('{} moved {}% over the last 5 days'.format(d['ticker'], percent_change))

                rating = 0
                if d['analystConsensus'] == 'StrongBuy':
                    rating += 1
                if d['bestAnalystConsensus'] == 'StrongBuy':
                    rating += 1
                if 'Buy' in d['newsSentimentData']['label']:
                    rating += 1
                try:
                    if 'Buy' in d['mediaBuzzData']['label']:
                        rating += 1
                except Exception:
                    pass
                try:
                    if d['hedgeFundSentimentData']['label'] == 'Positive':
                        rating += 1
                except Exception:
                    pass
                try:
                    if 'Buy' in d['investorSentimentData']['label']:
                        rating += 1
                except Exception:
                    pass
                try:
                    if d['bloggerSentimentData']['label'] == 'Bullish':
                        rating += 1
                except Exception:
                    pass
                
                strong_buy_stocks.append({'ticker': d['ticker'], 'company': d['company'], 'rating': rating, 
                                            'moved': percent_change})

            for stock_item in strong_buy_stocks:
                stock = stock_item['ticker']
                #print('DEBUG', stock)
                sys.stdout.write('.')
                sys.stdout.flush()

                data = get_stock_info(stock)
                if not data:
                    print('stock ticker {} not found in yahoo finance'.format(stock))
                    continue
                # check which market it's in
                exchange_name = data['chart']['result'][0]['meta']['exchangeName']
                if exchange_name not in ['NYQ', 'NMS']:
                        print('stock ticker {} in different exchange {}'.format(stock, exchange_name))
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

                change_low_to_market_price = round(stock_price - stock_low, 3)

                stock_info.append({'symbol': stock, 'company': stock_item['company'], 
                                    'rating': stock_item['rating'], 'market_price': stock_price, 
                                    'low': stock_low, 'high': stock_high, 'volume': stock_volume,
                                    'change_low_to_high': change_low_to_high,
                                    'change_low_to_market_price': change_low_to_market_price,
                                    'moved': stock_item['moved']})
            
            # sort stocks
            if tradealgo == 'lowtomarket':
                biggest_movers = sorted(stock_info, key = lambda i: i['change_low_to_market_price'], reverse = True)
            elif tradealgo == 'rating':
                biggest_movers = sorted(stock_info, key = lambda i: i['rating'], reverse = True)
            elif tradealgo == 'moved':
                biggest_movers = sorted(stock_info, key = lambda i: i['moved'], reverse = True)

            stock_picks = biggest_movers[0:MAX_NUM_STOCKS]
            print('\n')

            print(datetime.now(tz=TZ).isoformat())
            print('today\'s stocks {}'.format(stock_info))
            print('\n')
            print('today\'s picks {}'.format(stock_picks))
            print('\n')

        # buy stocks
        # check stock prices at 9:30am EST (market open) and continue to check for the next 1.5 hours
        # to see if stock is going down or going up, when the stock starts to go up, buy
        if datetime.today().weekday() in [0,1,2,3,4] and datetime.now(tz=TZ).hour == 9 \
            and datetime.now(tz=TZ).minute == 30:  # 9:30am EST

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
                    buy_price = stock_price_buy * NUM_SHARES
                    if num_prices >= 5 and went_up > went_down and equity >= buy_price:
                        buy_time = datetime.now(tz=TZ).isoformat()
                        print(buy_time)
                        api.submit_order(
                            symbol=stock['symbol'],
                            qty=NUM_SHARES,
                            side='buy',
                            type='market',
                            time_in_force='day'
                        )
                        print('placed buy order of stock {} ({}) for ${} (vol {})'.format(
                            stock['symbol'], stock['company'], stock_price_buy, stock['volume']))
                        total_buy_price += buy_price
                        stock_bought_prices.append([stock['symbol'], stock_price_buy, buy_time])
                        bought_stocks.append(stock)
                        equity -= buy_price
                    
                    stock_prices.append([stock['symbol'], stock_price_buy])

                # sleep and check prices again after 2 min if time is before 11:00am EST
                if len(stock_bought_prices) == MAX_NUM_STOCKS or \
                    equity == 0 or \
                    (datetime.now(tz=TZ).hour == 11 and datetime.now(tz=TZ).minute >= 0):  # 11:00am EST
                    break
                else:
                    time.sleep(120)
            
            print(datetime.now(tz=TZ).isoformat())
            print('sent buy orders for {} stocks, market price ${}'.format(len(bought_stocks), round(total_buy_price, 2)))

        # sell stocks
        # check stock prices at 11:00am EST and continue to check until 1:00pm EST to
        # see if it goes up by x percent, sell it if it does
        # when the stock starts to go down starting at 1:00pm EST, sell or 
        # sell at end of day 3:30pm EST
        if datetime.today().weekday() in [0,1,2,3,4] and datetime.now(tz=TZ).hour == 11 \
            and datetime.now(tz=TZ).minute >= 0:  # 11:00am EST

            stock_prices = []

            stock_sold_prices = []

            stock_data_csv = [['ticker', 'company', 'buy', 'buy time', 'sell', 'sell time', 'profit', 'percent', 'vol sod', 'vol sell']]

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
                        api.submit_order(
                            symbol=stock['symbol'],
                            qty=NUM_SHARES,
                            side='sell',
                            type='market',
                            time_in_force='day'
                        )
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
                print('selling any remaining stocks...')

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
                        if (num_prices >= 15 and went_down > went_up) or (datetime.now(tz=TZ).hour == 15 \
                            and datetime.now(tz=TZ).minute >= 30):  # 3:30pm EST:
                            stockinfo = [ x for x in stock_bought_prices if x[0] is stock['symbol'] ]
                            stock_price_buy = stockinfo[0][1]
                            buy_time = stockinfo[0][2]
                            diff = round(stock_price_sell - stock_price_buy, 2)
                            change_perc = round((stock_price_sell - stock_price_buy) / stock_price_buy * 100, 2)
                            sell_time = datetime.now(tz=TZ).isoformat()
                            print(sell_time)
                            api.submit_order(
                                symbol=stock['symbol'],
                                qty=NUM_SHARES,
                                side='sell',
                                type='market',
                                time_in_force='day'
                            )
                            stock_data = get_stock_info(stock['symbol'])
                            stock_vol_now = stock_data['chart']['result'][0]['indicators']['quote'][0]['volume'][0]
                            print('placed sell order of stock {} ({}) for ${} (diff ${} {}%) (vol {})'.format(
                                stock['symbol'], stock['company'], stock_price_sell, diff, change_perc, stock_vol_now))
                            sell_price = stock_price_sell * NUM_SHARES
                            stock_data_csv.append([stock['symbol'], stock['company'], stock_price_buy, buy_time, 
                                                    stock_price_sell, sell_time, diff, change_perc, stock['volume'], stock_vol_now])
                            stock_sold_prices.append([stock['symbol'], stock_price_sell, sell_time])
                            equity += sell_price

                    # sleep and check prices again after 2 min if time is before 4:00pm EST
                    if len(stock_sold_prices) == len(bought_stocks) or \
                        (datetime.now(tz=TZ).hour == 16 and datetime.now(tz=TZ).minute >= 0):  # 4:00pm EST
                        break
                    else:
                        time.sleep(120)

                # sold all stocks or market close

                percent = round((equity - START_EQUITY) / START_EQUITY * 100, 2)
                equity = round(equity, 2)
                print(datetime.now(tz=TZ).isoformat())
                print('*** PERCENT {}%'.format(percent))
                print('*** EQUITY ${}'.format(equity))

                # print out summary of today's buy/sells on alpaca

                todays_buy_sell = get_eod_change_percents()
                print(datetime.now(tz=TZ).isoformat())
                print(todays_buy_sell) 
                print('********************')
                print('TODAY\'S PROFIT/LOSS')
                print('********************')
                total_profit = 0
                n = 0
                for k, v in todays_buy_sell.items():
                    change_str = '{}{}'.format('+' if v['change']>0 else '', v['change'])
                    print('{} {}%'.format(k, change_str))
                    stock_data_csv.append([k, '', '', '', '', '', '', change_str, '', ''])
                    total_profit += v['change']
                    n += 1
                print('-----------')
                sum_str = '{}{}%'.format('+' if v['change']>0 else '', round(total_profit, 2))
                avg_str = '{}{}%'.format('+' if v['change']>0 else '', round(total_profit/n, 2))
                print('*** SUM {}'.format(sum_str))
                print('*** AVG {}'.format(avg_str))

                # write csv

                now = datetime.now(tz=TZ).date().isoformat()

                f = open('stocks_{0}_{1}.csv'.format(tradealgo, now), 'w')

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

                # set equity back to start value to not reinvest any gains
                if equity > START_EQUITY:
                    equity = START_EQUITY

        print(datetime.now(tz=TZ).isoformat(), '$ zzz...')
        time.sleep(60)


if __name__ == "__main__":
    main()