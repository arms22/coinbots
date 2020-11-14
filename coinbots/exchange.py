# -*- coding: utf-8 -*-
import logging
import asyncio
from .api import CCAPI
from .cctypes import type_converter
from .utils import dotdict
from collections import defaultdict

class ExchangeError(Exception):
    pass

class Exchange:

    ProductSpecs = {
        'btc_jpy':dotdict({
            'round_price':int,
            'round_amount':lambda x:round(x,8)
        }),
    }

    def __init__(self, apiKey, secret):
        self.private_api_enabled = len(apiKey) and len(secret)
        self.api = CCAPI(apiKey, secret)
        self.logger = logging.getLogger(__name__)

    def _get_data(self, res, default, errfrom, subfield=None):
        success = res.get('success',0)
        if success:
            if subfield:
                data = res.get(subfield, default)
            else:
                data = res
            return type_converter(data)
        else:
            error = res.get('error', '')
            raise ExchangeError(f'{error} in {errfrom}')

    async def order(self, pair, side, amount, rate, stop_loss_rate=None):
        spec = Exchange.ProductSpecs[pair]
        amount = spec.round_amount(amount)
        params = {
            'pair':pair
        }
        if stop_loss_rate:
            stop_loss_rate = spec.round_price(stop_loss_rate)
            params['stop_loss_rate'] = stop_loss_rate
        if rate:
            rate = spec.round_price(rate)
            params['rate'] = rate
            params['amount'] = amount
            params['order_type'] = side.lower()
        else:
            if side == 'buy':
                params['market_buy_amount'] = amount
            else:
                params['amount'] = amount
            params['order_type'] = 'market_'+side.lower()
        res = await self.api.orders(**params)
        orderRes = self._get_data(res, {}, f'orders with {pair} {side} {amount} {rate} {stop_loss_rate}')
        orderRes['executed_amount'] = 0
        orderRes['status'] = 'open'
        return orderRes

    async def cancel(self, orderRes):
        res = await self.api.cancel(orderRes['id'])
        self._get_data(res, orderRes, f'cancel with {orderRes["pair"]} {orderRes["id"]}')
        orderRes['status'] = 'cancel'
        return orderRes

    async def get_orders(self, pair=None):
        res = await self.api.orders_opens()
        return self._get_data(res, [], 'orders_opens', 'orders')

    async def get_my_trades(self, pair=None, count=None, since=None, end=None, order=None):
        params = {}
        if count:
            params['limit'] = count
        if since:
            params['starting_after'] = since
        if end:
            params['ending_before'] = end
        if order:
            params['order'] = order
        res = await self.api.transactions(**params)
        trades = self._get_data(res, [], 'transactions', 'data')
        if pair:
            trades = [t for t in trades if t['pair']==pair]
        for t in trades:
            base = t['pair'].split('_')[0]
            t['amount'] = abs(t['funds'][base])
        return trades

    async def balance(self):
        res = await self.api.balance()
        return self._get_data(res, {}, 'balance')

if __name__ == '__main__':
    from pprint import pprint as pp

    async def main():
        apiKey = ''
        secret = ''
        api = Exchange(apiKey, secret)

        # order = await api.order('mona_jpy','buy',1,90)
        # pp(order)

        # orders = await api.get_orders()
        # pp(orders)

        # order = await api.cancel(order)
        # pp(order)

        trades = await api.get_my_trades()
        pp(trades)

        # balance = await api.balance()
        # pp(balance)

        await api.api.close()

    asyncio.get_event_loop().run_until_complete(main())
