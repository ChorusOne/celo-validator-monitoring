# Celo Validator Monitor Slack Bot

**Credits:**
This is Celo monitoring bot is adapted from dsrc labs.
- [Original source code](https://github.com/dsrvlabs/celo-validator-monitoring)
- [dsrvlabs GitHub](https://github.com/dsrvlabs)

---

## The Bot

This bot send an alert to Slack channel when:
- (1) your validator does not produce a block for last 30 minutes.
- (2) your validator resumed and produced blocks for last 30 minutes.
- (3) Celo network does not produce blocks for 5 minutes.
- (4) Celo network resumed and produce blocks again.

We use 30 mins for validator and 5 mins for Celo network in Baklava testnet.
You can edit code to change above time intervals :)

dsrv labs also participate in TGCSO. For more details, please visit https://github.com/dsrvlabs/celo.

## Setup

Prerequisite: `python3` and `pip` installed on your environment.
```shell
$ # See: https://github.com/slackapi/python-slackclient
$ pip3 install slackclient
$ # See: https://github.com/erdewit/nest_asyncio
$ pip3 install nest_asyncio
$ chmod +x celo_slack_monitor_bot.py
$
$ # Set environment variables:
$ export CELO_VALIDATOR_NAME="Stark Industries"
$ export CELO_VALIDATOR_SIGNER_ADDRESS="0x3...0"
$ export CELO_MONITOR_SLACK_API_TOKEN="A...A"
$ export CELO_MONITOR_SLACK_CHANNEL_NAME="my celo channel name"
```

## Run

```shell
$ nohup ./celo_slack_monitor_bot.py &
```

## Alert Messages

When your validator does not produce blocks for last 30 minutes:

```
[Alerting] {validator} Celo validator has not produced any blocks last 30 minutes
```

When your validator resumed and produced blocks for last 30 minutes:

```
[OK] {validator} Celo validator has restored to producing blocks.
```

When Celo network does not produce blocks for 5 minutes:
```
[Chain stopped] Celo network has been stopped last 5 minutes.
```

When Celo network resumed and produce blocks again:
```
[Chain stopped] Celo network has been stopped, too.
```
