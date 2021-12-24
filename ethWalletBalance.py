import os.path
import sys
import json
import requests
import logging
from web3 import Web3

logging.basicConfig(level=logging.INFO, format='%(asctime)s -- %(levelname)s: %(message)s')


def main():
    config = get_config('config.json')
    if validate_config(config):
        wallet_address = config['wallet_address']
        coinmarket_api_key = config['api']['coinmarketcap']['key']
        moralis_api_key = config['api']['moralis']['key']
        moralis_api_node = config['api']['moralis']['node']

        web3 = get_web3(moralis_api_node)

        if web3.isConnected():
            validated_web3_wallet_address = web3.toChecksumAddress(wallet_address)

            logging.info('Token Profile for Wallet: {}'.format(validated_web3_wallet_address))

            # get native eth balance
            get_eth_balance(web3, validated_web3_wallet_address, coinmarket_api_key, moralis_api_key)

            # get erc20 tokens for wallet
            get_erc20_balance(web3, validated_web3_wallet_address, moralis_api_key)
        else:
            logging.info('Web3 Connection Failure')
    else:
        logging.error('Config Validation Failed: Populate Values')
        sys.exit()


def get_config(config_file_name):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config_location = dir_path + '/' + config_file_name
    with open(config_location) as config_file:
        config = json.load(config_file)
    return config


def validate_config(config):
    try:
        wallet_address = config['wallet_address']
        coinmarket_api_key = config['api']['coinmarketcap']['key']
        moralis_api_key = config['api']['moralis']['key']
        moralis_api_node = config['api']['moralis']['node']

        if wallet_address == "":
            return False
        elif moralis_api_key == "":
            return False
        elif moralis_api_node == "":
            return False
        elif coinmarket_api_key == "":
            return False
        return True
    except Exception as e:
        logging.error(e)
        return False


def get_erc20_balance(web3, wallet_address, moralis_api_key):
    headers = {
        'x-api-key': moralis_api_key
    }

    # get all erc20 token addresses
    erc20_token_list_query = 'https://deep-index.moralis.io/api/v2/{0}/erc20?chain=eth'.format(wallet_address)
    response = requests.request("GET", erc20_token_list_query, headers=headers)

    # get balance for each token address
    for erc_20_token in response.json():
        try:
            token_address = erc_20_token['token_address']
            validated_token_address = web3.toChecksumAddress(token_address)

            contract = web3.eth.contract(address=validated_token_address, abi=get_config('erc20ABI.json'))

            balance_of = contract.functions.balanceOf(wallet_address).call()
            token_name = contract.functions.name().call()

            # get balance for each erc20 token address
            erc20_price_query = 'https://deep-index.moralis.io/api/v2/erc20/{}/price?chain=eth'.format(token_address)

            erc20_price_response = requests.request("GET", erc20_price_query, headers=headers)
            if erc20_price_response:
                erc20_wallet_quantity = web3.fromWei(balance_of, 'ether')
                erc20_usd_price = int(erc20_price_response.json()['usdPrice'])
                erc20_wallet_usd_value = erc20_wallet_quantity * erc20_usd_price
                if int(erc20_wallet_usd_value) > 0:
                    logging.info('\t ERC-20 Token: {}'.format(token_name))
                    logging.info('\t\t Token Address: {}'.format(token_address))
                    logging.info('\t\t Quantity: {:,}'.format(erc20_wallet_quantity))
                    logging.info('\t\t Total USD Value: ${:,.2f}'.format(erc20_wallet_usd_value))
        except Exception as e:
            logging.error(e)


def get_eth_balance(web3, token_address, coinmarket_api_key, moralis_api_key):
    token = 'Ethereum'
    headers = {
        'x-api-key': moralis_api_key
    }
    native_balance_query = 'https://deep-index.moralis.io/api/v2/{0}/balance?chain=eth'.format(token_address)
    try:
        response = requests.request("GET", native_balance_query, headers=headers)
        response_json = response.json()
        native_balance_amount = web3.fromWei(int(response_json['balance']), "ether")
        eth_price = int(get_token_price('ETH', coinmarket_api_key))
        usd_amount = eth_price * native_balance_amount
        logging.info('\t Token: {}'.format(token))
        logging.info('\t\t Quantity: {:,}'.format(native_balance_amount))
        logging.info('\t\t Total USD Value: ${:,.2f}'.format(usd_amount))
    except Exception as e:
        logging.error(e)


def get_web3(moralis_node):
    try:
        moralis_node = moralis_node
        web3 = Web3(Web3.HTTPProvider(moralis_node))
        return web3
    except Exception as e:
        logging.error(e)


def get_token_price(token_symbol, coinmarket_api_key):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest?symbol={0}'.format(token_symbol)

    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': coinmarket_api_key,
    }

    try:
        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            resp = response.json()
            current_price = resp['data'][token_symbol]['quote']['USD']['price']
            return current_price
        else:
            return False
    except Exception as e:
        logging.error(e)
        logging.error('Token not found coin market api: {}'.format(token_symbol))


if __name__ == '__main__':
    main()
