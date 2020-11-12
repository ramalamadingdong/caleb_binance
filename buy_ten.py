from urllib.request import urlopen
import yahoo_fin.stock_info as si 
import alpaca_trade_api as tradeapi
import datetime, pytz, holidays, json, time, sys

class Tee:
    def write(self, *args, **kwargs):
        self.out1.write(*args, **kwargs)
        self.out2.write(*args, **kwargs)
    def __init__(self, out1, out2):
        self.out1 = out1
        self.out2 = out2
    def flush(self):
        pass

import sys
sys.stdout = Tee(open("log.txt", "w"), sys.stdout)

### Globals ###
need_close_out = True
last_day_traded = ""

api = tradeapi.REST('BASE', 'PASSWORD', base_url='https://paper-api.alpaca.markets')

def buy(stock, qty):
    api.submit_order(
    symbol=stock,
    qty=qty,
    side='buy',
    type='market',
    time_in_force='gtc'
    )

def sell(stock, qty):
    api.submit_order(
    symbol=stock,
    qty=qty,
    side='sell',
    type='market',
    time_in_force='gtc'
    )

def morning_checkout():
    gainers = si.get_day_gainers()
    num_stocks_bought = 0
    for stock in gainers[0:20]['Symbol']:
        if (num_stocks_bought == 10):
            break
        stock_price = si.get_live_price(stock)
        moving_avg = si.get_data(stock, interval='1d')['close'][-2:].mean()         # check 2 day moving avg
        print(stock, stock_price)
        qty_d = int(100 / stock_price)
        if qty_d > 0 and moving_avg > 0:
            try:
                buy(stock, qty_d)
                num_stocks_bought += 1
            except:
                print("Couldn't Buy: ", stock)
                continue

def get_positions():
    positions = api.list_positions()
    return(positions)

def during_day(): #while the market is open loops every 30 seconds, buys shares in the morning, sells them at night and prints 
    clock = api.get_clock()
    tz = pytz.timezone('US/Eastern')
    global need_close_out, last_day_traded
    while clock.is_open:
        current_time = datetime.datetime.now(tz)
        if last_day_traded != current_time.day:
            print("Waiting 1 hr then buying out the shares for the day!")
            time.sleep(3600)
            morning_checkout()
            need_close_out = True
            last_day_traded = current_time.day
        else:
            pos = get_positions()
            for x in pos:
                total_profit = (float(x.current_price) - float(x.avg_entry_price))*float(x.qty)
                percent_profit = ((float(x.current_price) - float(x.avg_entry_price))/float(x.current_price))*100
                if percent_profit < -2:
                    print("dumping stock: ", x.symbol)
                    sell(x.symbol, x.qty)

############# Close Out #############

        if current_time.hour == 15 and need_close_out:
            print("Closing out the day!")
            night_closeout()
            need_close_out = False
        time.sleep(30)

def night_closeout():
    api.cancel_all_orders()
    positions = get_positions()
    for pos in positions:
        sell(pos.symbol, pos.qty)

while True:
    clock = api.get_clock()
    if clock.is_open:
        during_day()
    else:
        time.sleep(1800)