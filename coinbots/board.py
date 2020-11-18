# -*- coding: utf-8 -*-
import asyncio
from .streaming import Streaming
from .utils import stop_watch
from .cctypes import type_converter
from .api import CCAPI

class Board:

    def __init__(self,pair):
        self.pair = pair
        self.temp_bids = {}
        self.temp_asks = {}
        self.bids = []
        self.asks = []
        self._updated = False
        self._needs_sort = False
        self.cond = asyncio.Condition()
        # self._create = stop_watch(self._create)
        # self._update = stop_watch(self._update)
        # self.sort = stop_watch(self.sort)

    def _create(self, board):
        self.temp_bids = {b[0]:b[1] for b in board['bids']}
        self.temp_asks = {b[0]:b[1] for b in board['asks']}
        self.bids = [{'price':k,'size':v} for k,v in self.temp_bids.items()]
        self.asks = [{'price':k,'size':v} for k,v in self.temp_asks.items()]

    def _update(self, board):
        self.temp_bids.update({b[0]:b[1] for b in board['bids']})
        self.temp_asks.update({b[0]:b[1] for b in board['asks']})

    def sync(self, board):
        self._create(board)

    async def attach(self, streaming):
        await streaming.subscribe_channel(self.pair+'-orderbook',self._orderbook)
        self._updated = True
        self._needs_sort = False

    async def _orderbook(self, channel, board):
        async with self.cond:
            self._updated = True
            self._needs_sort = True
            self._update(board)
            self.cond.notify()

    def sort(self):
        if self._needs_sort:
            self._needs_sort = False
            self.temp_bids = {k:v for k,v in self.temp_bids.items() if v>0}
            self.temp_asks = {k:v for k,v in self.temp_asks.items() if v>0}
            self.bids = [{'price':k,'size':v} for k,v in sorted(self.temp_bids.items(),reverse=True)]
            self.asks = [{'price':k,'size':v} for k,v in sorted(self.temp_asks.items())]
        return self.bids, self.asks

    async def wait(self):
        async with self.cond:
            await self.cond.wait_for(lambda:self._updated)
            self._updated = False

if __name__ == "__main__":
    import argparse
    import logging

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--pair", dest='pair', type=str, default='btc_jpy')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.getLogger('socketio').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)

    async def main():
        streaming = Streaming(Streaming.SocketioSource())
        board = Board(args.pair)
        await board.attach(streaming)
        async def poll():
            count = 0
            while True:
                try:
                    await board.wait()
                    board.sort()
                    # bids = board.bids
                    # asks = board.asks
                    bids = [b for b in board.bids if b['size']>=0.1]
                    asks = [b for b in board.asks if b['size']>=0.1]
                    count += 1
                    print(count)
                    for b,a in zip(bids[:20],asks[:20]):
                        print(f'{b["price"]:<8.0f} {b["size"]:6.2f}|{a["size"]:<6.2f} {a["price"]:8.0f}')
                except Exception as e:
                    print(e)

        await asyncio.wait([streaming.start(),poll()])

    asyncio.get_event_loop().run_until_complete(asyncio.wait([main()]))
