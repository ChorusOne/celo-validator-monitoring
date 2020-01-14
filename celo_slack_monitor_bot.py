#!/usr/bin/env python3
# TODO: handle HTTP response errors

import asyncio
from datetime import datetime, timedelta
from functools import wraps
import logging
import os
import re
import time
from urllib.error import URLError
from urllib.request import urlopen

import nest_asyncio
nest_asyncio.apply()

# See: https://github.com/slackapi/python-slackclient
# Install:
# pip3 install slackclient
import slack

OK = 0; VALIDATOR_DOWN = 1; CHAIN_DOWN = 2

validator_name = os.environ.get('CELO_VALIDATOR_NAME', '...default validator name...')
validator_address = os.environ.get('CELO_VALIDATOR_SIGNER_ADDRESS', '...default validator address...')
validator_threshold = timedelta(minutes = 30)
chain_threshold = timedelta(minutes = 5)
check_period_sec = 60
initial_status = OK

client = slack.WebClient(token=os.environ['CELO_MONITOR_SLACK_API_TOKEN'])

slack_channel_name = os.environ.get('CELO_MONITOR_SLACK_CHANNEL_NAME', '...default slack channel name...')

url = 'https://baklava-blockscout.celo-testnet.org/address/%s/validations?type=JSON' % validator_address
blocks_url = 'https://baklava-blockscout.celo-testnet.org/blocks?type=JSON'
pattern = re.compile(b'data-from-now=\\\\"(.*?)\\\\"')

logging.basicConfig(level = logging.WARNING,
                    format = '%(asctime)s %(name)-14s %(levelname)-8s %(message)s',
                    filename = 'celo_slack_bot.log',
                    filemode = 'a')

celo_channel = [None] # access by reference
celo_channel[0] = slack_channel_name

# from https://stackoverflow.com/questions/538666/format-timedelta-to-string
def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('year',        60*60*24*365),
        ('month',       60*60*24*30),
        ('day',         60*60*24),
        ('hour',        60*60),
        ('minute',      60),
        ('second',      1)
    ]

    strings=[]
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value , seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings)

def fromisoformat(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f')

# from https://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
def retry(ExceptionToCheck, tries=4, delay=3.0, backoff=2.0):
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 0:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    logging.warning(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return None
        return f_retry # true decorator
    return deco_retry

@retry(URLError)
def get_last_validated_time():
    f = urlopen(url)
    response = f.read()
    f.close()
    
    match = pattern.search(response)
    # 2019-12-08 11:09:47.000000Z
    if match:
        return fromisoformat(match.group(1).decode('ascii')[:-1])
    else:
        return datetime.min

@retry(URLError)
def get_last_block_time():
    f = urlopen(blocks_url)
    response = f.read()
    f.close()
    
    match = pattern.search(response)
    if match:
        return fromisoformat(match.group(1).decode('ascii')[:-1])
    else:
        return datetime.min

def postSlackMessage(message):
    client.chat_postMessage(
        channel=slack_channel_name,
        text=message)
    logging.info('Posted message to Slack')
    return

async def background_task():
    postSlackMessage("Starting Celo Monitor...")
    
    status = initial_status

    # Run until it crashes:
    while True:
        if celo_channel[0] is not None:
            last_validated_time = get_last_validated_time()
            last_block_time = get_last_block_time()
            if last_validated_time is None or last_block_time is None:
                logging.warning('cannot probe Celo network status')
                # Seems to happen a lot, ignore:
                # postSlackMessage('[???] cannot probe Celo network status. Maybe baklava-blockscout.celo-testnet.org is down.')
                time.sleep(check_period_sec)
                continue
            
            logging.debug('loop - last validated time %s', last_validated_time)
            now = datetime.utcnow()
            if status == CHAIN_DOWN:
                if now - last_validated_time <= min(chain_threshold, validator_threshold):
                    logging.debug('ok')
                    postSlackMessage('[OK] Celo network got to work.')
                    status = OK
                elif now - last_block_time <= chain_threshold:
                    logging.debug('alert')
                    postSlackMessage('[Alerting] Celo network got to work but %s Celo validator has not produced any blocks yet.' % validator_name)
                    status = VALIDATOR_DOWN
            elif status == VALIDATOR_DOWN:
                if now - last_block_time > chain_threshold:
                    logging.debug('chain down')
                    postSlackMessage('[Chain stopped] Celo network has been stopped, too.')
                    status = CHAIN_DOWN
                elif now - last_validated_time <= validator_threshold:
                    logging.debug('ok')
                    postSlackMessage('[OK] %s Celo validator has restored to producing blocks.' % validator_name)
                    status = OK
            elif status == OK:
                if now - last_block_time > chain_threshold:
                    logging.debug('chain down')
                    postSlackMessage('[Chain Stopped] Celo network has been stopped last %s.' % td_format(chain_threshold))
                    status = CHAIN_DOWN
                elif now - last_validated_time > validator_threshold:
                    logging.debug('alert')
                    postSlackMessage('[Alerting] %s Celo validator has not produced any blocks last %s.' % (validator_name, td_format(validator_threshold)))
                    status = VALIDATOR_DOWN
        time.sleep(check_period_sec)
    logging.warning('background_task() exit')

asyncio.run(background_task())
