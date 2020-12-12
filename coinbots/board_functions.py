# -*- coding: utf-8 -*-
import asyncio
from math import fsum

def findPriceByDepth(board, depth):
    cumsum = 0
    for b in board:
        cumsum += b['size']
        if cumsum>=depth:
            break
    return b['price']

def depthForDistance(board, distance):
    cumsum = 0
    best = board[0]['price']
    for b in board:
        cumsum += b['size']
        if abs(best-b['price'])>=distance:
            break
    return cumsum

def filterBySize(board, size):
    return [b for b in board if b['size']>=size]

def binningBySize(board, size, round_price=int):
    total = 0
    buc = []
    ret = []
    for b in board:
        buc.append(b)
        total += b['size']
        if total >= size:
            ret.append({'size':total,'price':round_price(fsum(i['price']*i['size'] for i in buc)/total)})
            total = 0
            buc = []
    if len(buc):
        ret.append({'size':total,'price':round_price(fsum(i['price']*i['size'] for i in buc)/total)})
    return ret

def binningByPriceLadder(board, step, round_price=int):
    best = board[0]
    last = best['price']//step
    total = 0
    buc = []
    ret = []
    for b in board:
        curr = b['price']//step
        if last != curr:
            ret.append({'size':total,'price':round_price(fsum(i['price']*i['size'] for i in buc)/total)})
            last = curr
            total = 0
            buc = []
        buc.append(b)
        total += b['size']
    if len(buc):
        ret.append({'size':total,'price':round_price(fsum(i['price']*i['size'] for i in buc)/total)})
    return ret

if __name__ == "__main__":
    import argparse
    import logging
    from .board import Board
    from .streaming import Streaming

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--pair", dest='pair', type=str, default='FX_BTC_JPY')
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
                    print('\033[2J', end='')
                    await board.wait()
                    board.sort()
                    bids = board.bids[:20]
                    asks = board.asks[:20]
                    # bids = filterBySize(board.bids,0.1)[:50]
                    # asks = filterBySize(board.asks,0.1)[:50]
                    # bids = binningBySize(board.bids,1)[:20]
                    # asks = binningBySize(board.asks,1)[:20]
                    # bids = binningByPriceLadder(board.bids,100)[:50]
                    # asks = binningByPriceLadder(board.asks,100)[:50]
                    bid_range = bids[0]['price']-bids[-1]['price']
                    bid_depth = fsum(b['size'] for b in bids)
                    ask_range = asks[-1]['price']-asks[0]['price']
                    ask_depth = fsum(b['size'] for b in asks)
                    buy_sell = 'buy' if bid_depth>ask_depth else 'sell'
                    print(f'{bid_range:7} {bid_depth:5.1f}|{ask_depth:<5.1f} {ask_range:<7} {buy_sell:4}')
                    print(f'----')
                    for b,a in zip(bids,asks):
                        print(f'{b["price"]} {b["size"]:5.2f}|{a["size"]:<5.2f} {a["price"]}')
                except Exception as e:
                    print(e)

        await asyncio.wait([streaming.start(),poll()])

    asyncio.get_event_loop().run_until_complete(asyncio.wait([main()]))
