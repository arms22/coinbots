# -*- coding: utf-8 -*-
from collections import defaultdict

def _type_converter(data):
    if isinstance(data,list):
        return [_type_converter(dat) for dat in data]
    elif isinstance(data,dict):
        return {k:_CCTypes[k](v) if v else v for k,v in data.items()}
    return data

_CCTypes = defaultdict(lambda:lambda x:x, {
    'last': float,
    'bid': float,
    'ask': float,
    'high': float,
    'low': float,
    'volume': float,
    'amount':float,
    'rate':float,
    'pending_amount': float,
    'pending_market_buy_amount': float,
    'stop_loss_rate': float,
    'fee': float,
    'orders': _type_converter,
    'transactions': _type_converter,
    'funds': _type_converter,
    'btc': float,
    'btc_reserved': float,
    'fct': float,
    'etc': float,
    'jpy': float,
    'jpy_reserved': float,
    'bids': lambda bids:[[float(d[0]),float(d[1])] for d in bids],
    'asks': lambda asks:[[float(d[0]),float(d[1])] for d in asks],
})

type_converter = _type_converter
