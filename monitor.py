import requests
import jmespath
from time import sleep
import logging
import yaml
import sys

# Configure logging
logging.basicConfig(filename='oanda-trade.log',level=logging.INFO,format='%(asctime)s %(message)s')

# Load confguration file
with open("config.yaml", 'r') as stream:
    try:
        config = yaml.load(stream)
    except:
        logging.error("Could not load the config file")
        sys.exit(1)




# Whether trade or practice environment
environment = config['environment']

# Amount less from the current profit amount. Larger the value less closer to current price
MARGIN = float(config['margin'])

# Whether update is simulated
SIMULATE = config['simulate']

# Instruments precision
INSTRUMENTS = { 'BCO_USD': 3, 'NATGAS_USD': 3}

# Sleep time between each analysis
SLEEP = config['sleep']

# URL to get the trades
trade_url = config['access'][environment]['server'] + '/v3/accounts/' + config['access'][environment]['account'] + '/trades'

# Headers with authentication token
headers = { 'Authorization':'Bearer ' + config['access'][environment]['token'], 'Content-Type': 'application/json'}


# Function to get all the active trades
def getTrades():

    response = requests.get(trade_url,headers=headers)

    if response.status_code == 200:
        return jmespath.search('trades[*]',response.json())
    else:
        print "Error occurred while getting trades - " + response.json()['errorMessage']
        return []


# Update trade
def updateTrade(tradeId, stopPrice, instrument):
    logging.info("Updating trade "+  str(tradeId) + " with stop price " + str(stopPrice))

    stopPrice = round(stopPrice,INSTRUMENTS[instrument])

    update_url = trade_url + "/" + tradeId + "/orders"
    payload = '{ "stopLoss": { "price" : "' + str(stopPrice) + '"} }'

    if SIMULATE == 'yes':
        logging.info("Simuating update trade stop value to " + str(stopPrice))
    else:
        response = requests.put(update_url,data=payload, headers=headers)

        if response.status_code == 200:
            logging.info("Update trade : Successful")
        else:
            logging.info("Update trade : Failed [" +  response.json()['errorMessage'] +  "]")






# Perform analysis
def analyze():
    # Collect the active trades
    trades = getTrades()
    logging.info("Number of trades [" + str(len(trades)) + "]")

    # Iterate the trades and analyze each
    for trade in trades:

        trade_id = trade['id']
        unrealized_pl = float(trade['unrealizedPL'])
        units = int(trade['initialUnits'])
        price = float(trade['price'])
        instrument = trade['instrument']

        #logging.info("trade=" + trade_id +  ", units=" + str(units) + ", unrealized=" + str(unrealized_pl) + ", instrument=" + instrument + " @" +  str(price))


        # Check for the unrealized profit greater than $1.
        # We only interested on any trades at profit
        if unrealized_pl > 3:

            target_profit = unrealized_pl - MARGIN
            target_unit_profit = target_profit / units
            target_unit_price = price + target_unit_profit

            logging.info("trade" + trade_id + ", " + str(price) + "->"+ str(target_unit_price))

            # Only update if current stop price is less that traget price
            if 'stopLossOrder' in trade:
                current_stop_price = float(trade['stopLossOrder']['price'])
                logging.info("current_stop_loss=" + str(current_stop_price) + ", target_stop_loss=" + str(target_unit_price))
                if current_stop_price < target_unit_price:
                    updateTrade(trade_id, target_unit_price, instrument)
            else:
                updateTrade(trade_id, target_unit_price, instrument)

# -- Main --

if SIMULATE == 'yes':
    logging.info("** Simulated **")

# Continous loop
while (1 == 1):
    analyze()
    sleep(SLEEP)


