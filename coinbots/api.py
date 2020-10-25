# -*- coding: utf-8 -*-
import asyncio
import aiohttp
import json
import time
import hmac
import hashlib
import urllib.parse
from datetime import datetime, timedelta

class CCAPI:

    def __init__(self, apiKey='', secret=''):
        self.apiKey = apiKey
        self.secret = secret
        self.endpoint = 'https://coincheck.com'
        self.session = aiohttp.ClientSession()

    async def throttle(self):
        pass

    async def fetch(self, method, path, params=None):
        await self.throttle()
        return await self.fetch2(method, path, params)

    async def fetch2(self, method, path, params):
        url = self.endpoint+path
        data = None
        headers = {}
        if ('/api/exchange/orders' in path) or ('/api/accounts' in path):
            apiKey = self.apiKey
            secret = self.secret
            nonce = str(int(time.time() * 1000))
            if method == 'POST':
                data = json.dumps(params)
                params = None
                text = nonce + url + data
                headers = {'Content-Type':'application/json'}
            else:
                if params:
                    text = nonce + url + '?' + urllib.parse.urlencode(params)
                else:
                    text = nonce + url
            sign = hmac.new(bytes(secret.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()
            headers['ACCESS-KEY'] = apiKey
            headers['ACCESS-NONCE'] = nonce
            headers['ACCESS-SIGNATURE'] = sign
        async with self.session.request(method=method,url=url,params=params,data=data,headers=headers) as res:
            # http_response = await res.text()
            # http_status_code = res.status
            # http_status_text = res.reason
            # print(res.headers)
            json_response = await res.json()
        return json_response

    async def ticker(self, **kwargs):
        return await self.fetch('GET', '/api/ticker', params=kwargs)

    async def trades(self, **kwargs):
        return await self.fetch('GET', '/api/trades', params=kwargs)

    async def orderbooks(self, **kwargs):
        return await self.fetch('GET', '/api/order_books', params=kwargs)

    async def orders_rate(self, **kwargs):
        return await self.fetch('GET', '/api/exchange/orders/rate', params=kwargs)

    async def orders(self, **kwargs):
        return await self.fetch('POST', '/api/exchange/orders', params=kwargs)

    async def orders_opens(self):
        return await self.fetch('GET', '/api/exchange/orders/opens')

    async def cancel(self, order_id):
        return await self.fetch('DELETE', f'/api/exchange/orders/{order_id}')

    async def cancel_status(self, order_id):
        return await self.fetch('GET', '/api/exchange/orders/cancel_status', params={'id':order_id})

    async def transactions(self, **kwargs):
        return await self.pagination('/api/exchange/orders/transactions_pagination', **kwargs)

    async def balance(self):
        return await self.fetch('GET', '/api/accounts/balance')

    async def close(self):
        await self.session.close()

if __name__ == '__main__':

    async def main():
        apiKey = ''
        secret = ''
        api = CCAPI(apiKey, secret)

        # ticker = await api.ticker('btc_jpy')
        # print(ticker)

        # orderbooks = await api.orderbooks('btc_jpy')
        # print(orderbooks)

        # trades = await api.trades(pair='btc_jpy', limit=20)
        # print(trades)

        rate = await api.orders_rate(pair='btc_jpy', order_type='buy', amount='0.01')
        print(rate)

        # status = await api.cancel_status(1)
        # print(status)

        # orders_opens = await api.orders_opens()
        # print(orders_opens)

        # transactions = await api.transactions(ending_before=189947209, limit=100)
        # print(transactions)

        # balance = await api.balance()
        # print(balance)

        await api.close()
    asyncio.get_event_loop().run_until_complete(main())
