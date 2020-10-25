# -*- coding: utf-8 -*-
from collections import defaultdict

def _type_converter(data):
    if isinstance(data,list):
        return [_type_converter(dat) for dat in data]
    elif isinstance(data,dict):
        return {k:_CCTypes[k](v) for k,v in data.items()}
    return data

_CCTypes = defaultdict(lambda:lambda x:x, {
    'last': float,
    'bid': float,
    'ask': float,
    'high': float,
    'low': float,
    'volume': float,
    # 'timestamp': int,

    # 'id':int,
    'amount':float,
    'rate':float,
    # 'pair':str,
    # 'order_type':str,
    # 'created_at':str,

    # 'success': bool,
    # 'id': int,
    # 'rate': float,
    # 'amount': float,
    # 'order_type': str,
    'stop_loss_rate': float,
    # 'pair': str,
    # 'created_at': str'

    'bids': lambda bids:[[float(d[0]),float(d[1])] for d in bids],
    'asks': lambda asks:[[float(d[0]),float(d[1])] for d in asks],
})

type_converter = _type_converter
