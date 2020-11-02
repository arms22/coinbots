# -*- coding: utf-8 -*-
import queue
import logging
import logging.handlers

apiKey = ''
secret = ''

# ロギング設定
def loggingConf(filename='ccbot.log'):
    return {
        'version': 1,
        'formatters':{
            'simpleFormatter':{
                'format': '%(asctime)s %(levelname)s:%(name)s:%(message)s',
                'datefmt': '%Y/%m/%d %H:%M:%S'}},
        'handlers': {
            'fileHandler': {
                'formatter':'simpleFormatter',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'level': 'INFO',
                'filename': filename,
                'encoding': 'utf8',
                'when': 'D',
                'interval': 1,
                'backupCount': 5},
            'consoleHandler': {
                'formatter':'simpleFormatter',
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'stream': 'ext://sys.stderr'}},
        'loggers': {
            'socketio':{'level': 'WARNING'},
            'engineio':{'level': 'WARNING'}},
        'root': {
            'level': 'INFO',
            'handlers': ['fileHandler', 'consoleHandler']},
        'disable_existing_loggers': False
    }

# 非同期ロギング設定
def loggingQueueListener(filename='bitbot.log'):
    q = queue.Queue(-1)
    queue_handler = logging.handlers.QueueHandler(q)

    root = logging.getLogger()
    root.addHandler(queue_handler)
    root.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.handlers.TimedRotatingFileHandler(filename,'D',1,5)
    file_handler.setFormatter(formatter)

    logging.getLogger('socketio').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)

    return logging.handlers.QueueListener(q, console_handler, file_handler)
