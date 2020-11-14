# -*- coding: utf-8 -*-
import asyncio
from coinbots.strategy import Strategy
from coinbots.indicator import *
from time import time

class btcmm:
    async def run(self, ohlcv, strategy, **others):
        C = ohlcv.close.values[-1]
        dev = stdev(ohlcv.close,10).values[-1]
        devmax = stdev(change(ohlcv.close,10),1000).values[-1]
        target = max(dev,devmax)
        mid = C
        buylimit = mid-target
        selllimit = mid+target

        maxsize = 0.005
        delta_pos = strategy.position_size-maxsize
        buysize = min(maxsize-delta_pos,maxsize)
        sellsize = min(maxsize+delta_pos,maxsize)

        if delta_pos>0 and delta_pos<0.005:
            sellsize += delta_pos
        if delta_pos<0 and delta_pos>-0.005:
            buysize -= delta_pos

        if buysize>=0.005:
            await strategy.order('L','buy',size=buysize,limit=buylimit)
        else:
            await strategy.cancel('L')
        if sellsize>=0.005:
            await strategy.order('S','sell',size=sellsize,limit=selllimit)
        else:
            await strategy.cancel('S')

if __name__ == "__main__":
    import settings
    import logging
    import logging.config

    listener = settings.loggingQueueListener('btcmm.log')
    listener.start()
    logger = logging.getLogger("btcmm")

    strategy = Strategy(yourlogic=btcmm().run, interval=1)
    strategy.settings.symbol = 'BTC/JPY'
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret
    strategy.settings.minimum_interval = 5

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(asyncio.wait([strategy.start()]))
    except (KeyboardInterrupt, SystemExit):
        loop.run_until_complete(asyncio.wait([strategy.cancel_order_all()]))
    listener.stop()
