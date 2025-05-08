import logging

import requests

from agents.common.config import SETTINGS
from agents.utils.token_limiter import TokenLimiter

logger = logging.getLogger(__name__)

host = SETTINGS.COIN_HOST

id_maps = {}
platform_maps = {}
tokenizer = TokenLimiter()


def init_id_maps():
    url = host + '/api/v3/coins/list'
    response = send_http_request('get', url, {}, {}, False)
    if response:
        for item in response:
            id_maps[item['id']] = item
    else:
        raise Exception("Failed to fetch coin list from CoinGecko API.")
    url = host + '/api/v3/asset_platforms'
    response = send_http_request('get', url, {}, {}, False)
    if response:
        for item in response:
            platform_maps[item['id']] = item
    else:
        raise Exception("Failed to fetch asset platform list from CoinGecko API.")


def query_price_by_ids(symbols: str, vs_currencies: str) -> dict:
    """
    Query the price of a cryptocurrency by its ID.

    Args:
        symbols (str): coin symbol or coin name, comma-separated if querying more than 1 coin. Defaults to "bitcoin".
        vs_currencies (str): target currency of coins, comma-separated if querying more than 1 currency. Defaults to "usd".

    Returns:
        dict: price(s) of cryptocurrency.
    """
    logger.info(f'Querying price of {symbols} in {vs_currencies}')
    ids = ",".join([to_id(symbol, "bitcoin") for symbol in symbols.split(',')])

    url = host + '/api/v3/simple/price'
    params = {
        'ids': ids,
        'vs_currencies': vs_currencies
    }
    headers = {
        'accept': 'application/json',
    }

    return send_http_request('get', url, headers, params)


def query_historical_data_by_ids(symbol: str,
                                 vs_currency: str,
                                 days: int) -> dict:
    """
    This endpoint allows you to get the historical chart data of a coin including time in UNIX, price, market cap and 24hrs volume based on particular coin id.

    Args:
        symbol (str): coin symbol or coin name. Defaults to "bitcoin".
        vs_currency (str): target currency of market data. Defaults to "usd".
        days (int): number of days to retrieve data for. Defaults to 7.
    Returns:
        dict: historical data of cryptocurrency.
    """
    logger.info(f'Querying historical data of {symbol} in {vs_currency}')
    id = to_id(symbol, "bitcoin")

    url = host + '/api/v3/coins/{id}/market_chart'
    url = url.format(id=id)
    params = {
        'vs_currency': vs_currency,
        'days': days
    }
    headers = {
        'accept': 'application/json',
    }

    data = send_http_request('get', url, headers, params)
    return data


def query_markets_by_currency(vs_currency: str,
                              symbols: str = None,
                              price_change_percentage: str = "24h") -> dict:
    """
    This endpoint allows you to query all the supported coins with price, market cap, volume and market related data.

    Args:
        vs_currency (str): target currency of coins and market data.Values range:["btc","eth","ltc","bch","bnb","eos","xrp","xlm","link","dot","yfi","usd","aed","ars","aud","bdt","bhd","bmd","brl","cad","chf","clp","cny","czk","dkk","eur","gbp","gel","hkd","huf","idr","ils","inr","jpy","krw","kwd","lkr","mmk","mxn","myr","ngn","nok","nzd","php","pkr","pln","rub","sar","sek","sgd","thb","try","twd","uah","vef","vnd","zar","xdr","xag","xau","bits","sats"] Defaults to "usd".
        symbols (str): coin symbol or coin name, comma-separated if querying more than 1 coin. Defaults to "bitcoin".
        price_change_percentage (str): include price change percentage timeframe, comma-separated if query more than 1 price change percentage timeframe Valid values: 1h, 24h, 7d, 14d, 30d, 200d, 1y Defaults to "24h".
    Returns:
        dict: markets where cryptocurrency is traded.
    """
    logger.info(f'Querying markets data of {vs_currency}')
    if symbols:
        ids = ",".join([to_id(symbol, "bitcoin") for symbol in symbols.split(',')])
    else:
        ids = None
    url = host + '/api/v3/coins/markets'
    params = {
        'vs_currency': vs_currency,
        'ids': ids,
        'price_change_percentage': price_change_percentage,
    }
    headers = {
        'accept': 'application/json',
    }

    return send_http_request('get', url, headers, params)


def query_token_price_by_id(platform: str, contract_addresses: str, vs_currencies: str):
    """
    This endpoint allows you to query the price of a token by its contract address.
    Args:
        platform (str): chain name, such as ethereum, polygon-pos, binance-smart-chain, arbitrum, optimism.
        contract_addresses (str): the contract addresses of tokens, comma-separated if querying more than 1 token's contract address
        vs_currencies (str): target currency of coins, comma-separated if querying more than 1 currency. Defaults to "usd".

    Returns:
        dict: price(s) of tokens.
    """
    url = host + '/api/v3/simple/token_price/{id}'
    id = platform_to_id(platform, None)
    url = url.format(id=id)
    params = {
        'contract_addresses': contract_addresses,
        'vs_currencies': vs_currencies
    }
    headers = {
        'accept': 'application/json',
    }

    return send_http_request('get', url, headers, params)


def query_top_gainers_losers(vs_currency: str, duration='24h', top_coins=50):
    """
    This endpoint allows you to query the top gainers and losers of the day.
    Args:
        vs_currency (str): target currency of coins. Defaults to "usd".
        duration (str): filter result by time range, valid values: 1h, 24h, 7d, 14d, 30d, 200d, 1y. Default value: 24h
        duration (int): filter result by market cap ranking (top 300 to 1000) or all coins (including coins that do not have market cap). Default value: 50
    Returns:
        dict: List top 30 gainers and losers.
    """
    url = host + '/api/v3/coins/top_gainers_losers'
    params = {
        'vs_currency': vs_currency,
        'duration': duration,
        'per_page': top_coins
    }
    headers = {
        'accept': 'application/json',
    }

    return send_http_request('get', url, headers, params)


def to_id(symbol: str, default: str = None) -> str:
    """
        Convert a symbol to an id.
    """
    symbol = symbol.lower().strip()
    if symbol in id_maps.keys():
        return symbol
    for k, v in id_maps.items():
        if 'symbol' in v and v['symbol'].lower() == symbol:
            return k
    for k, v in id_maps.items():
        if 'name' in v and symbol in v['name'].lower():
            return k
    return default


def platform_to_id(platform: str, default: str = None) -> str:
    platform = platform.lower().strip()
    if platform in platform_maps.keys():
        return platform
    for k, v in platform_maps.items():
        if 'name' in v and v['name'].lower() == platform:
            return k
    for k, v in platform_maps.items():
        if 'native_coin_id' in v and platform in v['native_coin_id'].lower():
            return k
    return default


def send_http_request(method: str,
                      url: str,
                      headers: dict,
                      params: dict,
                      limit_tokens=True,
                      api_key=SETTINGS.COIN_API_KEY) -> dict:
    try:
        headers = headers or {}
        if api_key:
            headers['x-cg-pro-api-key'] = api_key

        response = requests.request(method, url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if limit_tokens:
                # Truncate response based on token count
                return tokenizer.limit_tokens(data)
            return data
        else:
            logger.error(f'Failed to query markets data: {response.status_code} {response.text}')
            return {"error": "request error"}
    except Exception as e:
        logger.error(f"Error sending HTTP request: {e}")
    return {}


def query_listings_historical(date: str):
    """
    Returns a ranked and sorted list of all cryptocurrencies for a historical UTC date.

    Args:
        date (str): date (Unix or ISO 8601) to reference day of snapshot. It is recommended to send an ISO date format like "2019-10-10" without time.

    Returns:
        dict: A dictionary containing the listing information.
    """

    url = SETTINGS.COIN_HOST_V2 + '/v1/cryptocurrency/listings/historical'
    params = {
        'date': date,
    }
    headers = {
        'accept': 'application/json',
        'X-CMC_PRO_API_KEY': SETTINGS.COIN_API_KEY_V2
    }
    return send_http_request('get', url, headers, params, api_key=None)


def query_OHLCV_historical(symbol: str):
    url = SETTINGS.COIN_HOST_V2 + '/v2/cryptocurrency/ohlcv/historical'
    params = {
        'symbol': symbol,
        'time_start': '2024-09-19',
        'time_end': '2024-12-19',
    }
    headers = {
        'accept': 'application/json',
        'X-CMC_PRO_API_KEY': SETTINGS.COIN_API_KEY_V2
    }
    return send_http_request('get', url, headers, params, api_key=None)


if __name__ == '__main__':
    # init_id_maps()
    # print(query_price_by_ids("bitcoin", "usd"))
    # print(query_historical_data_by_ids("bitcoin", "usd", 7))
    # print(query_markets_by_currency("usd", "bitcoin", "24h"))
    # print(query_token_price_by_id("ethereum", "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", "usd"))
    # print(query_top_gainers_losers("usd"))
    print(query_listings_historical("2024-01-05"))
    print(query_OHLCV_historical("BTC,ETH"))
    pass
