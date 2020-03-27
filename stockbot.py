#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""stockbot.py - get recommended buy and strong buy stocks
daily from Nasdaq.com and get prices from Yahoo and determine
which stocks moved the most the previous day, sort those by 
largest movers (based on open/close $) and buy those stocks
if they are going up. At the end of the market day, sell 
any purchased stocks.

Copyright (C) Chris Park 2020
"""

import os, sys
import csv
import requests
import time
from datetime import datetime
from pytz import timezone
from random import randint
import alpaca_trade_api as tradeapi


STOCKBOT_VERSION = '0.1-b.1'
__version__ = STOCKBOT_VERSION

TZ = timezone('America/New_York')

api = tradeapi.REST('PKJUK5SQ6REUFTCV7QJC', 'dsm/Ywauqgx8YUEZJXa/lNREMds6fly745P3FT13', 'https://paper-api.alpaca.markets')

HIGH_PRICE = 100
LOW_PRICE = 20
NUM_STOCKS = 10
NUM_SHARES = 5
SELL_PERCENT_GAIN = 3


def get_stock_info(stock):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/{0}?region=US&lang=en-US&includePrePost=false&interval=1d&range=1d&corsDomain=finance.yahoo.com&.tsrc=finance".format(stock)
    r = requests.get(url)
    stock_data = r.json()
    return stock_data


def get_stock_price(data):
    stock_price = data['chart']['result'][0]['meta']['regularMarketPrice']
    return stock_price


def get_closed_orders(stock_picks):
    closed_orders = api.list_orders(
        status='closed',
        limit=NUM_STOCKS
    )
    closed_orders_list = []
    for stock in stock_picks:
        closed_orders = [o for o in closed_orders if o.symbol == stock['symbol']]
        closed_orders_list.append(closed_orders_list)
    return closed_orders_list


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
    if tradealgo not in ['rating', 'lowtomarket']:
        print('required arg missing, use rating or lowtomarket')
        sys.exit(1)
except IndexError:
    print('required arg missing, use rating or lowtomarket')
    sys.exit(1)
print('Trade algo: {}'.format(tradealgo))

# Get our account information.
account = api.get_account()

# Check if our account is restricted from trading.
if account.trading_blocked:
    print('Account is currently restricted from trading.')


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
            
            strong_buy_stocks.append({'ticker': d['ticker'], 'company': d['company'], 'rating': rating})

        for stock_item in strong_buy_stocks:
            stock = stock_item['ticker']
            #print(stock)
            sys.stdout.write('.')
            sys.stdout.flush()

            data = get_stock_info(stock)

            try:
                stock_high = round(data['chart']['result'][0]['indicators']['quote'][0]['high'][0], 2)

                stock_low = round(data['chart']['result'][0]['indicators']['quote'][0]['low'][0], 2)

                change_low_to_high = round(stock_high - stock_low, 2)

                stock_price = get_stock_price(data)

                stock_volume = data['chart']['result'][0]['indicators']['quote'][0]['volume'][0]
            except Exception:
                pass

            if stock_price >= HIGH_PRICE or stock_price <= LOW_PRICE:
                continue

            change_low_to_market_price = round(stock_price - stock_low, 2)

            stock_info.append({'symbol': stock, 'company': stock_item['company'], 
                                'rating': stock_item['rating'], 'market_price': stock_price, 
                                'low': stock_low, 'high': stock_high, 'volume': stock_volume,
                                'change_low_to_high': change_low_to_high,
                                'change_low_to_market_price': change_low_to_market_price})
        
        # sort stocks
        if tradealgo == 'lowtomarket':
            biggest_movers = sorted(stock_info, key = lambda i: i['change_low_to_market_price'], reverse = True)
        elif tradealgo == 'rating':
            biggest_movers = sorted(stock_info, key = lambda i: i['rating'], reverse = True)

        stock_picks = biggest_movers[0:NUM_STOCKS]
        print('\n')

        print(datetime.now(tz=TZ).isoformat())
        print('today\'s stocks {}'.format(stock_info))
        print('today\'s picks {}'.format(stock_picks))

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

        buy_price = 0
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

                # buy the stock if there are 5 records of it and it's gone up
                if num_prices >= 5 and went_up > went_down:
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
                    buy_price += stock_price_buy * NUM_SHARES
                    stock_bought_prices.append([stock['symbol'], stock_price_buy, buy_time])
                    bought_stocks.append(stock)
                
                stock_prices.append([stock['symbol'], stock_price_buy])

            # sleep and check prices again after 2 min if time is before 11:00am EST
            if len(stock_bought_prices) == NUM_STOCKS or \
                (datetime.now(tz=TZ).hour == 11 and datetime.now(tz=TZ).minute == 0):  # 11:00am EST
                break
            else:
                time.sleep(120)
                print('Last 100 closed orders: {}'.format(get_closed_orders(stock_picks)))
        
        print(datetime.now(tz=TZ).isoformat())
        print('sent buy orders for {} stocks, market price ${}'.format(len(bought_stocks), round(buy_price, 2)))
        print('Last 100 closed orders: {}'.format(get_closed_orders(stock_picks)))

    # sell stocks
    # check stock prices at 11:00am EST and continue to check until 1:00pm EST to
    # see if it goes up by x percent, sell it if it does
    # when the stock starts to go down starting at 1:00pm EST, sell or 
    # sell at end of day 3:30pm EST
    if datetime.today().weekday() in [0,1,2,3,4] and datetime.now(tz=TZ).hour == 11 \
        and datetime.now(tz=TZ).minute == 0:  # 11:00am EST

        stock_prices = []

        stock_sold_prices = []

        profit = 0

        stock_data_csv = [['ticker', 'company', 'buy', 'buy time', 'sell', 'sell time', 'profit', 'percent', 'volume']]

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
                    print('placed sell order of stock {} ({}) for ${} (diff ${} {}%) (vol {})'.format(
                        stock['symbol'], stock['company'], stock_price_sell, diff, 
                        change_perc, stock['volume']))
                    profit += diff * NUM_SHARES
                    stock_data_csv.append([stock['symbol'], stock['company'], stock_price_buy, buy_time, 
                                            stock_price_sell, sell_time, diff, change_perc, stock['volume']])
                    stock_sold_prices.append([stock['symbol'], stock_price_sell, sell_time])
                else:
                    print(sell_time)
                    print('stock {} ({}) hasn\'t gone up enough to sell ${} (diff ${} {}%)'.format(
                        stock['symbol'], stock['company'], stock_price_sell, diff, change_perc))

            # sleep and check prices again after 2 min if time is before 1:00pm EST
            if len(stock_sold_prices) == len(bought_stocks) or \
                (datetime.now(tz=TZ).hour == 13 and datetime.now(tz=TZ).minute == 0):  # 1:00pm EST
                break
            else:
                time.sleep(120)
                print('Last 100 closed orders: {}'.format(get_closed_orders(stock_picks)))

        if len(stock_sold_prices) < len(bought_stocks) and \
            (datetime.now(tz=TZ).hour == 13 and datetime.now(tz=TZ).minute == 0):  # 1:00pm EST
        
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

                    # sell the stock if there are 10 records of it and it's gone down
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
                        print('placed sell order of stock {} ({}) for ${} (diff ${} {}%) (vol {})'.format(
                            stock['symbol'], stock['company'], stock_price_sell, diff, change_perc, 
                            stock['volume']))
                        profit += diff * NUM_SHARES
                        stock_data_csv.append([stock['symbol'], stock['company'], stock_price_buy, buy_time, 
                                                stock_price_sell, sell_time, diff, change_perc, stock['volume']])
                        stock_sold_prices.append([stock['symbol'], stock_price_sell, sell_time])

                # sleep and check prices again after 2 min if time is before 4:00pm EST
                if len(stock_sold_prices) == len(bought_stocks) or \
                    (datetime.now(tz=TZ).hour == 16 and datetime.now(tz=TZ).minute >= 0):  # 4:00pm EST
                    break
                else:
                    time.sleep(120)
                    print('Last 100 closed orders: {}'.format(get_closed_orders(stock_picks)))

            # sold all stocks or market close

            print('Last 100 closed orders: {}'.format(get_closed_orders(stock_picks)))

            if profit > 0:
                t = 'made'
            else:
                t = 'lost'
            profit = round(profit, 2)
            print('{} ${}'.format(t, profit))
            price_sold = round(buy_price + profit, 2)
            percent = round((price_sold - buy_price) / buy_price * 100, 2)
            print(datetime.now(tz=TZ).isoformat())
            print('percent {}%'.format(percent))
            print('balance ${}'.format(price_sold))

            # write csv

            now = datetime.now(tz=TZ).isoformat()

            f = open('stocks_{0}.csv'.format(now), 'w')

            with f:
                writer = csv.writer(f)
                for row in stock_data_csv:
                    writer.writerow(row)

    print('$ zzz')
    time.sleep(60)
