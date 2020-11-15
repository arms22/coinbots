# -*- coding: utf-8 -*-
import aiohttp
import asyncio
import logging
import json
import socketio
from datetime import datetime
from collections import deque, defaultdict
from time import time

class Streaming:

    def __init__(self, source):
        self.logger = logging.getLogger(__name__)
        self.source = source
        self.running = False
        self.subscribed_channels = {}
        self.endpoints = []
        self.callbacks = defaultdict(list)
        self.on_connect = None

    async def _on_data(self,channel,data):
        for cb in self.callbacks[channel]:
            await cb(channel,data)

    async def _subscribe_registred_channels(self):
        if len(self.subscribed_channels):
            for _subscribe in self.subscribed_channels.values():
                await _subscribe()

    async def _on_connect(self):
        if self.on_connect:
            await self.on_connect()
        await self._subscribe_registred_channels()

    async def add_endpoint(self, channel, endpoint):
        self.endpoints.append(endpoint)
        await self.subscribe_channel(channel,endpoint.callback)
        return endpoint

    async def subscribe_channel(self, channel, callback):
        self.callbacks[channel].append(callback)
        if channel not in self.subscribed_channels:
            async def _subscribe():
                await self.source.subscribe(channel)
            self.subscribed_channels[channel] = _subscribe
            await _subscribe()

    async def unsubscribe_channel(self, channel, callback):
        if callback in self.callbacks[channel]:
            self.callbacks[channel].remove(callback)
            if len(self.callbacks[channel])==0:
                await self.source.unsubscribe(channel)
                if channel in self.subscribed_channels:
                    del self.subscribed_channels[channel]

    # Public
    async def get_trades_endpoint(self, pair, maxlen=100):
        ep = Streaming.BufferedEndpoint(maxlen=maxlen)
        return await self.add_endpoint(pair+'-trades',ep)

    async def get_orderbook_endpoint(self, pair):
        ep = Streaming.BufferedEndpoint()
        return await self.add_endpoint(pair+'-orderbook',ep)

    async def get_trades2_endpoint(self, pair, maxlen=100):
        ep = Streaming.BufferedEndpoint(maxlen=maxlen)
        return await self.add_endpoint(pair+'-trades-v2',ep)

    async def start(self):
        if self.running == False:
            self.running = True
            self.logger.info('Start Streaming')
            await asyncio.wait([self.source.start(self._on_data,self._on_connect,self.logger)])
            self.logger.info('Stop Streaming')

    async def stop(self):
        if self.running:
            self.running = False
            await self.source.stop()
            for ep in self.endpoints:
                await ep.shutdown()

    class Source:
        def __init__(self):
            pass

        async def subscribe(self,channel,token):
            pass

        async def unsubscribe(self,channel):
            pass

        async def _disconnect(self):
            pass

        async def _run_loop(self):
            pass

        async def start(self, on_data, on_connect, logger):
            self.on_data = on_data
            self.on_connect = on_connect
            self.logger = logger
            self.running = True
            while self.running:
                try:
                    await self._run_loop()
                except Exception as e:
                    logger.exception(e)
                if self.running:
                    await asyncio.sleep(5)

        async def stop(self):
            self.running = False
            await self._disconnect()

    class SocketioSource(Source):
        def __init__(self):
            super().__init__()
            self.sio = None
            self.sio_connected = False

        async def _on_disconnect(self):
            self.logger.info('sio disconnected')
            self.sio_connected = False

        async def _on_connect(self):
            self.logger.info('sio connected')
            self.sio_connected = True
            await self.on_connect()

        async def _on_trades(self,trades):
            if isinstance(trades[0],list):
                channel = trades[0][1]+'-trades-v2'
                dat = [{'id':t[0],'pair':t[1],'rate':float(t[2]),'amount':float(t[3]),'order_type':t[4]} for t in trades]
            else:
                t = trades
                channel = t[1]+'-trades'
                dat = {'id':t[0],'pair':t[1],'rate':float(t[2]),'amount':float(t[3]),'order_type':t[4]}
            await self.on_data(channel,dat)

        async def _on_orderbook(self,ob):
            channel = ob[0]+'-orderbook'
            dat = {}
            dat['asks'] = [[float(b[0]),float(b[1])] for b in ob[1].get('asks',[])]
            dat['bids'] = [[float(b[0]),float(b[1])] for b in ob[1].get('bids',[])]
            await self.on_data(channel,dat)

        async def subscribe(self,channel):
            if self.sio_connected:
                await self.sio.emit('subscribe',channel)

        async def unsubscribe(self,channel):
            if self.sio_connected:
                await self.sio.emit('unsubscribe',channel)

        async def _disconnect(self):
            if self.sio_connected:
                await self.sio.disconnect()

        async def _run_loop(self):
            self.sio = socketio.AsyncClient(reconnection=False)
            self.sio.on('connect', self._on_connect)
            self.sio.on('disconnect', self._on_disconnect)
            self.sio.on('trades', self._on_trades)
            self.sio.on('orderbook', self._on_orderbook)
            await self.sio.connect('wss://ws.coincheck.com', transports = ['websocket'])
            await self.sio.wait()

    class WebsocketSource(Source):
        def __init__(self):
            super().__init__()
            self.ws = None
            self.ws_connected = False

        async def subscribe(self,channel):
            if self.ws_connected:
                await self.ws.send_json({'type': 'subscribe', 'channel': channel})

        async def unsubscribe(self,channel):
            if self.ws_connected:
                await self.ws.send_json({'type': 'unsubscribe', 'channel': channel})

        async def _disconnect(self):
            if self.ws_connected:
                await self.ws.close()

        async def _run_loop(self):
            async with aiohttp.ClientSession() as client:
                self.ws = await client.ws_connect('wss://ws-api.coincheck.com/')
                self.ws_connected = True
                self.logger.info('wss connected')
                await self.on_connect()
                while True:
                    msg = await self.ws.receive()
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        message = json.loads(msg.data)
                        channel = ''
                        dat = {}
                        if len(data)==5:
                            channel = data[1]+'-trades'
                            dat['id'] = data[0]
                            dat['pair'] = data[1]
                            dat['rate'] = float(data[2])
                            dat['amount'] = float(data[3])
                            dat['order_type'] = data[4]
                        elif len(data)==2:
                            channel = data[0]+'-orderbook'
                            dat['asks'] = [ [float(b[0]),float(b[1])] for b in data[1].get('asks',[])]
                            dat['bids'] = [ [float(b[0]),float(b[1])] for b in data[1].get('bids',[])]
                        await self.on_data(channel,dat)
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        self.ws_connected = False
                        self.logger.info('wss disconnected')
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        self.ws_connected = False
                        self.logger.info('wss error')
                        break

    class Endpoint:

        def __init__(self):
            self.cond = asyncio.Condition()
            self.closed = False
            self.data = None
            self.updated = False
            self.suspend_count = 0

        def update(self, channel, data):
            self.data = data
            return True

        async def callback(self, channel, data):
            async with self.cond:
                self.updated = self.update(channel,data)
                if self.updated:
                    self.cond.notify_all()

        def _blocking(self):
            return (self.suspend_count==0 and self.updated==True) or (self.closed)

        async def wait(self):
            async with self.cond:
                result = await self.cond.wait_for(self._blocking)
            return result

        async def suspend(self, flag):
            async with self.cond:
                if flag:
                    self.suspend_count += 1
                else:
                    self.suspend_count = max(self.suspend_count-1, 0)
                    if self.suspend_count == 0:
                        self.cond.notify_all()

        async def shutdown(self):
            async with self.cond:
                self.closed = True
                self.cond.notify_all()

        def fetch_data(self):
            return self.data

        async def get_data(self, blocking=False):
            async with self.cond:
                if blocking:
                    await self.cond.wait_for(self._blocking)
                data = self.fetch_data()
                self.updated = False
            return data

    class BufferedEndpoint(Endpoint):

        def __init__(self, maxlen=100):
            super().__init__()
            self.deq = deque(maxlen=maxlen)

        def update(self, channel, data):
            self.deq.append(data)
            return True

        def fetch_data(self):
            data = list(self.deq)
            self.deq.clear()
            return data

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--symbol", dest='symbol', type=str, default='BTCJPY')
    args = parser.parse_args()

    async def public_main():
        # streaming = Streaming(Streaming.WebsocketSource())
        streaming = Streaming(Streaming.SocketioSource())
        executions_ep = await streaming.get_trades_endpoint('btc_jpy')
        book_ep = await streaming.get_orderbook_endpoint('btc_jpy')
        async def poll():
            while True:
                try:
                    executions = await executions_ep.get_data(blocking=True)
                    print(executions)
                    # ob = await book_ep.get_data(blocking=True)
                    # print(ob)
                except Exception as e:
                    print(e)
        await asyncio.wait([streaming.start(),poll()])

    asyncio.get_event_loop().run_until_complete(asyncio.wait([public_main()]))
