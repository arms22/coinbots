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

    async def create(self, board):
        async with self.cond:
            self._updated = True
            self._needs_sort = False
            self._create(board)
            self.cond.notify()

    def _update(self, board):
        self.temp_bids.update({b[0]:b[1] for b in board['bids']})
        self.temp_asks.update({b[0]:b[1] for b in board['asks']})

    async def update(self, board):
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

    async def _on_connect(self):
        await self.streaming.subscribe_channel(self.pair+'-orderbook',self._depth_diff)
        api = CCAPI()
        ob = await api.orderbooks(pair=self.pair)
        self._create(type_converter(ob))
        await api.close()

    async def _depth_diff(self, channel, board):
        await self.update(board)

    async def start(self):
        self.streaming = Streaming(Streaming.WebsocketSource())
        self.streaming.on_connect = self._on_connect
        await asyncio.wait([self.streaming.start()])

    async def wait(self):
        async with self.cond:
            await self.cond.wait_for(lambda:self._updated)
            self._updated = False

    async def stop(self):
        await self.streaming.stop()

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
        board = Board(args.pair)
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
                    for b,a in zip(bids[:10],asks[:10]):
                        print(f'{b["price"]:8.3f} {b["size"]:10.3f} | {a["size"]:<10.3f} {a["price"]:8.3f}')
                except Exception as e:
                    print(e)

        await asyncio.wait([board.start(),poll()])

    asyncio.get_event_loop().run_until_complete(asyncio.wait([main()]))
