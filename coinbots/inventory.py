# -*- coding: utf-8 -*-
import asyncio
import logging
from collections import OrderedDict, defaultdict, deque
from itertools import chain
from operator import itemgetter
from math import fsum
from datetime import datetime, timedelta
import time

class Inventory:

    class Position:

        def __init__(self, spec, initial_positions=[]):
            self.spec = spec
            self.positions = deque(initial_positions)
            self.compute_summary()

        def add(self, p):
            """建玉追加"""
            self.positions.append(p.copy())
            while len(self.positions)>=2:
                r = self.positions.pop()
                l = self.positions.popleft()
                if r['side']==l['side']:
                    # 売買方向が同じなら取り出したポジションを戻す
                    self.positions.append(r)
                    self.positions.appendleft(l)
                    break
                else:
                    if l['amount'] >= r['amount']:
                        # 決済
                        l['amount'] = self.spec.round_amount(l['amount'] - r['amount'])
                        if l['amount'] > 0:
                            # サイズが残っている場合、ポジションを戻す
                            self.positions.appendleft(l)
                    else:
                        # 決済
                        r['amount'] = self.spec.round_amount(r['amount'] - l['amount'])
                        if r['amount'] > 0:
                            # サイズが残っている場合、ポジションを戻す
                            self.positions.append(r)
            # 建玉情報更新
            self.compute_summary()

        def compute_summary(self):
            """サマリー計算"""
            positions = list(self.positions)
            if len(positions):
                ltp = positions[-1]['rate']
                self.long_size = self.spec.round_amount(fsum(p['amount'] for p in positions if p['side']=='buy'))
                self.short_size = self.spec.round_amount(fsum(p['amount'] for p in positions if p['side']=='sell'))
                self.position_size = self.long_size - self.short_size
                self.position_avg_price = self.spec.round_price(fsum(p['rate']*p['amount'] for p in positions)/(self.long_size+self.short_size))
                self.position_pnl = (ltp - self.position_avg_price) * self.position_size
            else:
                self.long_size = 0
                self.short_size = 0
                self.position_avg_price = 0
                self.position_size = 0
                self.position_pnl = 0

    OPEN_STATUS = ['open']

    def __init__(self, spec):
        self.logger = logging.getLogger(__name__)
        self.spec = spec
        self.active_orders = {}
        self.nonactive_orders = {}
        self.position = Inventory.Position(self.spec)
        self.order_for_myid = defaultdict(lambda:{\
            'status': 'cancel',
            })

    def new_order(self, myid, orderRes):
        orderRes['myid'] = myid
        orderRes['trades'] = {}
        self.active_orders[orderRes['id']] = orderRes
        self.order_for_myid[myid] = orderRes

    def get_order(self, myid):
        return self.order_for_myid[myid]

    def get_active_orders(self):
        return [o for o in self.order_for_myid.values() if o['status'] in Inventory.OPEN_STATUS]

    def get_untracking_active_orders(self):
        my_orders = {o['id']:o for o in self.order_for_myid.values()}
        return [o for o in self.active_orders.values() if o['status'] in Inventory.OPEN_STATUS and o['id'] not in my_orders]

    def on_execute(self, o, tr):
        # 注文情報更新
        if tr['id'] not in o['trades']:
            o['trades'][tr['id']] = tr
            trades = o['trades'].values()
            executed_amount = self.spec.round_amount(fsum(t['amount'] for t in trades))
            average_price = self.spec.round_price(fsum(t['amount']*t['rate'] for t in trades)/executed_amount)
            remaining_amount = self.spec.round_amount(o['amount']-executed_amount)
            o['executed_amount'] = executed_amount
            o['average_price'] = average_price
            o['remaining_amount'] = remaining_amount
            if executed_amount>=o['amount']:
                o['status'] = 'filled'
            self.logger.info('EXE {myid} {status} {order_type} {average_price} {executed_amount}/{amount} {id}'.format(**o))
            # ポジション追加
            self.position.add(tr)
            self.logger.info('POSITION: size {0} avg {1:.1f} pnl {2:.1f}'.format(\
                self.position.position_size,
                self.position.position_avg_price,
                self.position.position_pnl))

    async def start(self):
        await asyncio.wait([
            self.remove_nonactive_orders()])

    async def remove_nonactive_orders(self):
        while True:
            try:
                # 5分待ち
                await asyncio.sleep(300)
                # ノンアクティブオーダー削除
                self.logger.info('Remove Nonactive Orders active {0} nonactive {1}'.format(len(self.active_orders),len(self.nonactive_orders)))
                active_orders = {k:v for k,v in self.active_orders.items() if v['status'] in Inventory.OPEN_STATUS}
                nonactive_orders = {k:v for k,v in self.active_orders.items() if v['status'] not in Inventory.OPEN_STATUS}
                self.active_orders = active_orders
                self.nonactive_orders = nonactive_orders
            except Exception as e:
                self.logger.exception(e)

    def check_my_trades(self,trades):
        trades = sorted(trades, key=itemgetter('id'))
        for e in trades:
            order_id = e['order_id']
            order = self.active_orders.get(order_id,None) or self.nonactive_orders.get(order_id,None)
            if order:
                self.on_execute(order,e)
