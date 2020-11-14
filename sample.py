# -*- coding: utf-8 -*-
import asyncio
from coinbots.strategy import Strategy
from coinbots.indicator import *

class Sample:
    async def run(self, executions, ohlcv, strategy, **others):
        C = ohlcv.close.values[-1]
        await strategy.order('L','buy',0.01,C*0.8)

if __name__ == "__main__":
    import settings
    import logging
    import logging.config

    logging.config.dictConfig(settings.loggingConf('sample.log'))
    logger = logging.getLogger("sample")

    strategy = Strategy(yourlogic=Sample().run, interval=10)
    strategy.settings.symbol = 'BTC/JPY'
    strategy.settings.apiKey = settings.apiKey
    strategy.settings.secret = settings.secret

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([strategy.start()]))
