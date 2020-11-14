# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from collections import deque, defaultdict
from datetime import datetime
from .utils import dotdict
from math import sqrt

class OHLCVBuilder:

    def __init__(self, maxlen=100, timeframe=60, disable_rich_ohlcv=False):
        self.disable_rich_ohlcv = disable_rich_ohlcv
        self.ohlcv = defaultdict(lambda:deque(maxlen=maxlen))
        self.last = None
        self.timeframe = timeframe

    def create_boundary_ohlcv(self, executions):
        if len(executions)==0:
            if self.last is not None:
                e = self.last.copy()
                e['amount'] = 0
                e['order_type'] = ''
                executions.append(e)
        if len(executions):
            self.last = executions[-1]
            for k,v in self.make_ohlcv(executions).items():
                self.ohlcv[k].append(v)
        return self.to_rich_ohlcv()

    def to_rich_ohlcv(self):
        rich_ohlcv = dotdict()
        for k,v in self.ohlcv.items():
            rich_ohlcv[k] = np.array(v)
        if not self.disable_rich_ohlcv:
            rich_ohlcv = pd.DataFrame.from_dict(rich_ohlcv)
        return rich_ohlcv

    def make_ohlcv(self, executions):
        price = [e['rate'] for e in executions]
        buy = [e for e in executions if e['order_type'] == 'buy']
        sell = [e for e in executions if e['order_type'] == 'sell']
        ohlcv = dotdict()
        ohlcv.open = price[0]
        ohlcv.high = max(price)
        ohlcv.low = min(price)
        ohlcv.close = price[-1]
        ohlcv.buy_volume = sum(e['amount'] for e in buy)
        ohlcv.sell_volume = sum(e['amount'] for e in sell)
        ohlcv.volume = ohlcv.buy_volume + ohlcv.sell_volume
        ohlcv.volume_imbalance = ohlcv.buy_volume - ohlcv.sell_volume
        ohlcv.buy_count = len(buy)
        ohlcv.sell_count = len(sell)
        ohlcv.trades = ohlcv.buy_count + ohlcv.sell_count
        ohlcv.imbalance = ohlcv.buy_count - ohlcv.sell_count
        ohlcv.average = sum(price) / len(price)
        return ohlcv
