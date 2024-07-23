from web3 import Web3, HTTPProvider
import const
import pandas as pd
from requests import get, post
import time
import datetime
import streamlit as st
import os
import random
import ast

#### INFURA

# Get the keys from the environment variable
INFURA_KEYS = os.environ.get("INFURA_KEYS")

if INFURA_KEYS is None:
    raise ValueError("INFURA_KEYS is not set")

# Split the keys into a list
INFURA_KEYS_LIST = INFURA_KEYS.split(',')

# Select a key at random
INFURA_KEY = random.choice(INFURA_KEYS_LIST)

#### DUNE

# Get the keys from the environment variable
DUNE_KEYS = os.environ.get("DUNE_KEYS")

if DUNE_KEYS is None:
    raise ValueError("DUNE_KEYS is not set")

# Split the keys into a list
DUNE_KEYS_LIST = DUNE_KEYS.split(',')

# Select a key at random
DUNE_API_KEY = random.choice(DUNE_KEYS_LIST)

HEADER = {"x-dune-api-key": DUNE_API_KEY}


#######################################################################################################################
# Functions to fetch data from Dune
#######################################################################################################################

# Use this function to generate a URL to call the API.
def make_api_url(module, action, ID):
    url = "https://api.dune.com/api/v1/" + module + "/" + ID + "/" + action
    return url


# Takes in the query ID and engine size (default - "medium").
# Returns the execution ID of the instance which is executing the query.
def execute_query(query_id, engine="free"):
    url = make_api_url("query", "execute", query_id)
    params = {
        "performance": engine,
    }
    response = post(url, headers=HEADER, params=params)
    execution_id = response.json()['execution_id']
    return execution_id


# Takes in an execution ID from the above function.
# Returns the status response object.
def get_query_status(execution_id):
    url = make_api_url("execution", "status", execution_id)
    response = get(url, headers=HEADER)
    return response


# Takes in an execution ID from the above function.
# Returns the results response object
def get_query_results(execution_id):
    url = make_api_url("execution", "results", execution_id)
    response = get(url, headers=HEADER)
    return response


# Takes in an execution ID from the above function.
# Cancels the ongoing execution of the query. Returns the response object.
def cancel_query_execution(execution_id):
    url = make_api_url("execution", "cancel", execution_id)
    response = get(url, headers=HEADER)
    return response


def execute_query_and_get_addresses(query_id, engine="free"):
    # Execute query
    execution_id = execute_query(query_id, engine)

    # # Get query status
    # response = get_query_status(execution_id)

    response = get_query_results(execution_id)
    res_json = response.json()

    # Check if the query execution is completed
    while res_json['state'] != 'QUERY_STATE_COMPLETED':
        # Pause for a short while before checking again
        time.sleep(1)
        res_json = get_query_results(execution_id).json()

    # Extract addresses from the response
    addresses = [row['address'] for row in res_json['result']['rows']]

    return addresses


#######################################################################################################################

# w3 = Web3(HTTPProvider(f"https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}"))
w3 = Web3(HTTPProvider(f"https://mainnet.infura.io/v3/{INFURA_KEY}"))


def get_user_position(user_address, data_provider_address=const.DATA_PROVIDER):
    # Convert data_provider_address to checksum format
    data_provider_address = Web3.to_checksum_address(data_provider_address)
    abi = [{"inputs": [{"internalType": "address", "name": "user", "type": "address"}], "name": "getUserPositions",
            "outputs": [{"components": [{"components": [{"internalType": "address", "name": "vault", "type": "address"},
                                                        {"internalType": "uint256", "name": "balance",
                                                         "type": "uint256"}],
                                         "internalType": "struct IAggregatorDataProvider.UserVaultData[]",
                                         "name": "userVaultData", "type": "tuple[]"}, {"components": [
                {"internalType": "address", "name": "strategy", "type": "address"},
                {"internalType": "uint256", "name": "assetBalance", "type": "uint256"},
                {"internalType": "uint256", "name": "borrowBalance", "type": "uint256"},
                {"internalType": "uint256", "name": "collateralBalance", "type": "uint256"}],
                                            "internalType": "struct IAggregatorDataProvider.UserStrategyData[]",
                                            "name": "userStrategyData",
                                            "type": "tuple[]"}],
                         "internalType": "struct IAggregatorDataProvider.AggregatedUserData", "name": "arg_0",
                         "type": "tuple"}], "stateMutability": "view", "type": "function"}]

    # Instantiate the contract
    data_provider_contract = w3.eth.contract(address=data_provider_address, abi=abi)

    data = data_provider_contract.functions.getUserPositions(Web3.to_checksum_address(user_address)).call()

    return data


def update_and_save_address_list(loaded_address_log, triggered_block=w3.eth.block_number, file_path='address_log.csv'):
    """
    Updates the address log DataFrame with a new row and saves it to a CSV file.

    Parameters:
    loaded_address_log (DataFrame): The original address log DataFrame.
    triggered_block (int): The block to be added to the DataFrame.
    file_path (str): The path of the CSV file to save the updated DataFrame to.

    Returns:
    DataFrame: The updated address log DataFrame.

    Raises:
    Exception: If an error occurs while executing the query or saving the DataFrame.
    """
    try:
        address_log_df = loaded_address_log.copy()

        user_address_list = execute_query_and_get_addresses(const.QUERY_ID)

        # Creating a new DataFrame with the new data
        new_row = pd.DataFrame({'block': [triggered_block], 'user_address_list': [user_address_list]})

        # Concatenating the new row with the existing DataFrame
        address_log_df = pd.concat([address_log_df, new_row], ignore_index=True)

        address_log_df.to_csv(file_path, index=False)

        return address_log_df
    except Exception as e:
        print(f"An error occurred: {e}")
        raise



def get_user_position_data(user_address_df):

    # Find the maximum value in the "block" column
    max_block_value = user_address_df['block'].max()

    # Extract values from other columns corresponding to the maximum 'block' value
    max_block_row = user_address_df[user_address_df['block'] == max_block_value]

    user_address_list = max_block_row['user_address_list'].iloc[0]

    # Convert the string back to a list
    user_address_list = ast.literal_eval(user_address_list)

    #  user_address_list = execute_query_and_get_addresses(const.QUERY_ID)
    data_name = ['assetBalance', 'borrowBalance', 'collateralBalance']
    column_name = ['user']

    for i in range(len(const.STRATEGY_NAME)):
        for j in range(len(data_name)):
            column_name.append(f'{const.STRATEGY_NAME[i]}_{data_name[j]}')

    df = pd.DataFrame(columns=column_name)

    for i in range(len(user_address_list)):
        # Call the getStrategy function with the provided strategy address and block number
        strategy_data = get_user_position(user_address_list[i])
        # Create a new row for each user
        df.loc[i] = [
            user_address_list[i],
            strategy_data[1][0][1] / 1e18, strategy_data[1][0][2] / 1e18, strategy_data[1][0][3] / 1e18,
            strategy_data[1][1][1] / 1e18, strategy_data[1][1][2] / 1e18, strategy_data[1][1][3] / 1e18,
            strategy_data[1][2][1] / 1e18, strategy_data[1][2][2] / 1e18, strategy_data[1][2][3] / 1e18,
            strategy_data[1][3][1] / 1e18, strategy_data[1][3][2] / 1e18, strategy_data[1][3][3] / 1e18
        ]

    return df


def get_price_low(oracle_address, block=w3.eth.block_number):
    abi = [{"inputs": [], "name": "getPrices",
            "outputs": [{"internalType": "bool", "name": "_isBadData", "type": "bool"},
                        {"internalType": "uint256", "name": "_priceLow", "type": "uint256"},
                        {"internalType": "uint256", "name": "_priceHigh", "type": "uint256"}],
            "stateMutability": "view", "type": "function"}]
    address = Web3.to_checksum_address(oracle_address)

    contract = w3.eth.contract(address=address, abi=abi)

    prices = contract.functions.getPrices().call(block_identifier=int(block))

    price_low = prices[1] / 1e18

    return price_low


def get_virtual_price(pool_address, block=w3.eth.block_number):
    abi = [{"stateMutability": "view",
            "type": "function",
            "name": "get_virtual_price",
            "inputs": [],
            "outputs": [{"name": "arg_0", "type": "uint256"}]}]
    address = Web3.to_checksum_address(pool_address)

    contract = w3.eth.contract(address=address, abi=abi)

    prices = contract.functions.get_virtual_price().call(block_identifier=int(block))

    virtual_price = prices / 1e18

    return virtual_price


def compute_user_ltv(sturdy_data_strategy_file, user_address_df, oracle_address_list=const.ORACLE_ADDRESS_LIST):
    user_position_df = get_user_position_data(user_address_df)

    # Find the maximum value in the "block" column
    max_block_value = sturdy_data_strategy_file['block'].max()

    # Extract values from other columns corresponding to the maximum 'block' value
    max_block_row = sturdy_data_strategy_file[sturdy_data_strategy_file['block'] == max_block_value]

    # A loop to go through the number of strategies as no. of strategies = no. of oracle contracts
    for i in range(len(const.STRATEGY_LIST)):
        # Column name to retrieve max LTV which is fetched and stored in sturdyDataStrategyV1.csv file
        max_ltv_col_name = f'maxLTV{const.STRATEGY_NAME[i]}'
        max_ltv = max_block_row[max_ltv_col_name].iloc[0]

        price_low = get_price_low(const.ORACLE_ADDRESS_LIST[i])

        user_position_df[f'{const.STRATEGY_NAME[i]}_LTV'] = user_position_df[
                                                                f'{const.STRATEGY_NAME[i]}_borrowBalance'] * price_low / \
                                                            user_position_df[
                                                                f'{const.STRATEGY_NAME[i]}_collateralBalance']
        user_position_df[f'{const.STRATEGY_NAME[i]}_liq_price'] = (max_ltv / 100) * user_position_df[
            f'{const.STRATEGY_NAME[i]}_collateralBalance'] / user_position_df[f'{const.STRATEGY_NAME[i]}_borrowBalance']
        user_position_df[f'{const.STRATEGY_NAME[i]}_share_price'] = price_low

    return user_position_df


def accumulate_block_with_no_data(latest_block_with_data):

    latest_block_number = w3.eth.block_number
    print(latest_block_number)
    historic_block_list = []

    start_block_number = closest_lower_value(latest_block_with_data) + const.BLOCK_INTERVAL
    # print(f'start_block_number = {start_block_number}')

    while start_block_number < latest_block_number:
        # Add the current block number to the list
        historic_block_list.append(start_block_number)
        # Compute the next block number
        start_block_number += const.BLOCK_INTERVAL

    historic_block_list.append(latest_block_number)

    return historic_block_list


def closest_lower_value(latest_block_with_data, starting_number=const.BLOCK_START):
    # print(f'starting_number = {starting_number}')
    target_number = latest_block_with_data
    # Calculate the number of steps needed to reach the target number
    steps = (target_number - starting_number) // 1200

    # Calculate the closest lower value
    closest_lower = starting_number + steps * 1200

    return closest_lower


# Strategy Pair Calls
def pair_call_interest(address, block):
    # Convert the address to checksum format
    pair_address = Web3.to_checksum_address(address)

    # ABI for the pricePerShare function
    function_abi = [{"inputs": [], "name": "previewAddInterest",
                     "outputs": [{"internalType": "uint256", "name": "_interestEarned", "type": "uint256"},
                                 {"internalType": "uint256", "name": "_feesAmount", "type": "uint256"},
                                 {"internalType": "uint256", "name": "_feesShare", "type": "uint256"}, {
                                     "components": [{"internalType": "uint32", "name": "lastBlock", "type": "uint32"},
                                                    {"internalType": "uint32", "name": "feeToProtocolRate",
                                                     "type": "uint32"},
                                                    {"internalType": "uint64", "name": "lastTimestamp",
                                                     "type": "uint64"},
                                                    {"internalType": "uint64", "name": "ratePerSec", "type": "uint64"},
                                                    {"internalType": "uint64", "name": "fullUtilizationRate",
                                                     "type": "uint64"}],
                                     "internalType": "struct SturdyPairCore.CurrentRateInfo",
                                     "name": "_newCurrentRateInfo", "type": "tuple"}, {
                                     "components": [{"internalType": "uint128", "name": "amount", "type": "uint128"},
                                                    {"internalType": "uint128", "name": "shares", "type": "uint128"}],
                                     "internalType": "struct VaultAccount", "name": "_totalAsset", "type": "tuple"}, {
                                     "components": [{"internalType": "uint128", "name": "amount", "type": "uint128"},
                                                    {"internalType": "uint128", "name": "shares", "type": "uint128"}],
                                     "internalType": "struct VaultAccount", "name": "_totalBorrow", "type": "tuple"}],
                     "stateMutability": "view", "type": "function"}]

    # Contract instance for the provided address and ABI
    contract = w3.eth.contract(address=pair_address, abi=function_abi)

    # Call the pricePerShare function with the provided block
    newCurrentRateInfo = contract.functions.previewAddInterest().call(block_identifier=int(block))

    # Extract the value inside _newCurrentRateInfo[3]
    rate_per_sec = newCurrentRateInfo[3][3]

    return rate_per_sec


def pair_call_feerate(address, block):
    # Convert the address to checksum format
    pair_address = Web3.to_checksum_address(address)

    # ABI for the currentRateInfo function
    function_abi = [{"inputs": [], "name": "currentRateInfo",
                     "outputs": [{"internalType": "uint32", "name": "lastBlock", "type": "uint32"},
                                 {"internalType": "uint32", "name": "feeToProtocolRate", "type": "uint32"},
                                 {"internalType": "uint64", "name": "lastTimestamp", "type": "uint64"},
                                 {"internalType": "uint64", "name": "ratePerSec", "type": "uint64"},
                                 {"internalType": "uint64", "name": "fullUtilizationRate", "type": "uint64"}],
                     "stateMutability": "view", "type": "function"}]

    # Contract instance for the provided address and ABI
    contract = w3.eth.contract(address=pair_address, abi=function_abi)

    # Call the currentRateInfo function with the provided block
    current_rate_info = contract.functions.currentRateInfo().call(block_identifier=int(block))

    # Extract the value of feeToProtocolRate from the tuple
    fee_to_protocol_rate = current_rate_info[1]

    return fee_to_protocol_rate


# Yearn Calls
# def fetch_pps(address, block):
#     # Convert the address to checksum format
#     yearn_address = Web3.to_checksum_address(address)
#
#     # ABI for the pricePerShare function
#     pricePerShare_abi = [{
#         "stateMutability": "view",
#         "type": "function",
#         "name": "pricePerShare",
#         "inputs": [],
#         "outputs": [{"name": "arg_0", "type": "uint256"}]
#     }]
#
#     # Contract instance for the provided address and ABI
#     yearn_pps = w3.eth.contract(address=yearn_address, abi=pricePerShare_abi)
#
#     # Call the pricePerShare function with the provided block
#     pps = yearn_pps.functions.pricePerShare().call(block_identifier=int(block))
#
#     return pps


# Data aggregator Calls
def get_strategy_data(strategy_address, oracle_address, pool_address, block_number,
                      data_provider_contract=const.DATA_PROVIDER):
    # Convert the data provider address to checksum format
    data_provider_address = Web3.to_checksum_address(data_provider_contract)

    get_strategy_abi = [
        {"inputs": [{"internalType": "address", "name": "_strategy", "type": "address"}], "name": "getStrategy",
         "outputs": [{"components": [{"internalType": "address", "name": "deployedAt", "type": "address"},
                                     {"internalType": "address", "name": "pair", "type": "address"}, {
                                         "components": [{"internalType": "address", "name": "asset", "type": "address"},
                                                        {"internalType": "string", "name": "assetSymbol",
                                                         "type": "string"},
                                                        {"internalType": "uint256", "name": "assetDecimals",
                                                         "type": "uint256"},
                                                        {"internalType": "address", "name": "collateral",
                                                         "type": "address"},
                                                        {"internalType": "string", "name": "collateralSymbol",
                                                         "type": "string"},
                                                        {"internalType": "uint256", "name": "collateralDecimals",
                                                         "type": "uint256"},
                                                        {"internalType": "address", "name": "rateContract",
                                                         "type": "address"},
                                                        {"internalType": "address", "name": "oracle",
                                                         "type": "address"},
                                                        {"internalType": "uint256", "name": "depositLimit",
                                                         "type": "uint256"},
                                                        {"internalType": "uint64", "name": "ratePerSec",
                                                         "type": "uint64"},
                                                        {"internalType": "uint64", "name": "fullUtilizationRate",
                                                         "type": "uint64"},
                                                        {"internalType": "uint32", "name": "feeToProtocolRate",
                                                         "type": "uint32"},
                                                        {"internalType": "uint32", "name": "maxOacleDeviation",
                                                         "type": "uint32"},
                                                        {"internalType": "uint256", "name": "lowExchangeRate",
                                                         "type": "uint256"},
                                                        {"internalType": "uint256", "name": "highExchangeRate",
                                                         "type": "uint256"},
                                                        {"internalType": "uint256", "name": "maxLTV",
                                                         "type": "uint256"},
                                                        {"internalType": "uint256", "name": "protocolLiquidationFee",
                                                         "type": "uint256"},
                                                        {"internalType": "uint256", "name": "totalAsset",
                                                         "type": "uint256"},
                                                        {"internalType": "uint256", "name": "totalCollateral",
                                                         "type": "uint256"},
                                                        {"internalType": "uint256", "name": "totalBorrow",
                                                         "type": "uint256"},
                                                        {"internalType": "uint256", "name": "version",
                                                         "type": "uint256"}],
                                         "internalType": "struct IAggregatorDataProvider.StrategyPairData",
                                         "name": "pairData", "type": "tuple"}],
                      "internalType": "struct IAggregatorDataProvider.StrategyData", "name": "arg_0", "type": "tuple"}],
         "stateMutability": "view", "type": "function"}]

    # Contract instance for the data provider
    data_provider_contract = w3.eth.contract(address=data_provider_address, abi=get_strategy_abi)

    # Call the getStrategy function with the provided strategy address and block number
    strategy_data = data_provider_contract.functions.getStrategy(strategy_address).call(
        block_identifier=int(block_number))

    # Extract relevant data from the returned tuple
    data = {
        'block': int(block_number),
        'collateral': strategy_data[2][3],
        'collateralSymbol': strategy_data[2][4],
        'ratePerSec': strategy_data[2][9],
        'fullUtilizationRate': strategy_data[2][10],
        'lowExchangeRate': get_price_low(oracle_address, block_number),
        'highExchangeRate': strategy_data[2][14] / 1e18,
        'maxLTV': strategy_data[2][15] / 1e3,
        'totalAsset': strategy_data[2][17] / 1e18,
        'totalCollateral': strategy_data[2][18] / 1e18,
        'totalBorrow': strategy_data[2][19] / 1e18,
        'newCurrentRateInfo': pair_call_interest(strategy_data[1], int(block_number)),
        'feeToProtocolRate': pair_call_feerate(strategy_data[1], int(block_number)),
        'virtualPrice': get_virtual_price(pool_address, block_number)
    }

    return data


def get_strategy_data_for_blocks(strategy_address, oracle_address, pool_address, block_numbers):
    strategy_data_list = []

    for block_number in block_numbers:
        try:
            strategy_data = get_strategy_data(strategy_address, oracle_address, pool_address, int(block_number))
            strategy_data_list.append(strategy_data)
        except Exception as e:
            # print(f"Error fetching data for block {block_number}: {e}")
            continue

    return pd.DataFrame(strategy_data_list)


def merge_strategy_data(historic_block_list, strategy_list=const.STRATEGY_LIST, oracle_list=const.ORACLE_ADDRESS_LIST,
                        pool_address_list=const.CURVE_POOL_LIST,
                        strategy_names=const.STRATEGY_NAME):
    data_list = []

    for i in range(len(strategy_list)):
        strategy_data = get_strategy_data_for_blocks(strategy_list[i], oracle_list[i], pool_address_list[i],
                                                     historic_block_list)
        strategy_data = strategy_data.add_suffix(strategy_names[i])
        strategy_data = strategy_data.rename(columns={f'block{strategy_names[i]}': 'block'})
        data_list.append(strategy_data)

    data_list_for_merging = data_list.copy()

    merged_df = data_list_for_merging[0]
    for df in data_list_for_merging[1:]:
        merged_df = pd.merge(merged_df, df, on='block', how='inner')
        merged_df = merged_df.rename(columns={f'block_x': 'block'})

    time_series_df = generate_time_series(historic_block_list)

    merged_df_ts = pd.merge(merged_df, time_series_df, on='block', how='inner')

    return merged_df_ts


# Yearn Calls
def fetch_pps(address, block):
    # Convert the address to checksum format
    yearn_address = Web3.to_checksum_address(address)

    # ABI for the pricePerShare function
    pricePerShare_abi = [{
        "stateMutability": "view",
        "type": "function",
        "name": "pricePerShare",
        "inputs": [],
        "outputs": [{"name": "arg_0", "type": "uint256"}]
    }]

    # Contract instance for the provided address and ABI
    yearn_pps = w3.eth.contract(address=yearn_address, abi=pricePerShare_abi)

    # Call the pricePerShare function with the provided block
    pps = yearn_pps.functions.pricePerShare().call(block_identifier=int(block))

    data = {
        'block': int(block),
        'pps': pps
    }

    return data


def get_pps_data_for_blocks(collateral_address, block_numbers):
    pps_data_list = []

    for block_number in block_numbers:
        try:
            pps_data = fetch_pps(collateral_address, int(block_number))
            pps_data_list.append(pps_data)
        except Exception as e:
            continue

    return pd.DataFrame(pps_data_list)


def merge_pps_data(historic_block_list_pps, collateral_list=const.COLLATERAL_LIST, strategy_names=const.STRATEGY_NAME):
    pps_data_list = []

    for i in range(len(collateral_list)):
        pps_data = get_pps_data_for_blocks(collateral_list[i], historic_block_list_pps)
        pps_data = pps_data.add_suffix(strategy_names[i])
        pps_data = pps_data.rename(columns={f'block{strategy_names[i]}': 'block'})
        pps_data_list.append(pps_data)

    pps_data_list_for_merging = pps_data_list.copy()

    merged_pps_df = pps_data_list_for_merging[0]
    for df in pps_data_list_for_merging[1:]:
        merged_pps_df = pd.merge(merged_pps_df, df, on='block', how='inner')
        merged_pps_df = merged_pps_df.rename(columns={f'block_x': 'block'})

    return merged_pps_df


def process_dataframe(df):
    # Create a copy of the DataFrame
    processed_df = df.copy()

    # Number of columns
    num_columns = len(processed_df.columns)

    # Create new columns by shifting existing columns by 180 rows
    for i in range(1, num_columns):
        new_column_name = f'{processed_df.columns[i]}_lagged'
        processed_df[new_column_name] = processed_df.iloc[:, i].shift(180)

    # Divide every column except the first one by 1e18
    for column in processed_df.columns[1:]:
        processed_df[column] /= 1e18

    # Calculate ROI for each column
    for i in range(1, num_columns):
        days = 30
        new_column_name = f'{processed_df.columns[i]}_APY'
        processed_df[new_column_name] = (1 + (
                (processed_df[processed_df.columns[i]] - processed_df[f'{processed_df.columns[i]}_lagged']) /
                processed_df[f'{processed_df.columns[i]}_lagged'])) ** (365.2425 / days) - 1

    # Calculate APR for each column
    for i in range(1, num_columns):
        compounding = 52
        new_column_name = f'{processed_df.columns[i]}_APR'
        processed_df[new_column_name] = compounding * (
                (processed_df[f'{processed_df.columns[i]}_APY'] + 1) ** (1 / compounding)) - compounding

    new_df = pd.DataFrame()
    new_df['block'] = processed_df['block']

    for i in range(1, num_columns):
        new_df[f'{processed_df.columns[i]}'] = processed_df[f'{processed_df.columns[i]}']
        # new_df[f'{processed_df.columns[i]}_APY'] = processed_df[f'{processed_df.columns[i]}_APY']
        new_df[f'{processed_df.columns[i]}_APR'] = processed_df[f'{processed_df.columns[i]}_APR']

    return new_df


def compute_master_data(pps_df, silo_df, strategy_name=const.STRATEGY_NAME):
    # df = pd.DataFrame()

    df = pd.merge(silo_df, pps_df, on='block', how='left')
    df.rename(columns={f'block_x': 'block'}, inplace=True)

    # df.drop(columns=['block_y'], inplace=True)

    output_data = pd.DataFrame()

    output_data['block'] = df['block']
    output_data['time'] = df['time']

    for i in range(4):
        output_data[f'reserveSize{strategy_name[i]}'] = df[f'totalAsset{strategy_name[i]}']
        output_data[f'currentBorrow{strategy_name[i]}'] = df[f'totalBorrow{strategy_name[i]}']
        output_data[f'utilization{strategy_name[i]}'] = df[f'totalBorrow{strategy_name[i]}'] / df[
            f'totalAsset{strategy_name[i]}']
        output_data[f'collateralApr_{strategy_name[i]}'] = df[f'pps{strategy_name[i]}_APR']
        # borrow_apy = new_current_rate * 31536000 / rate_precision * 100
        output_data[f'borrowApy_{strategy_name[i]}'] = df[f'newCurrentRateInfo{strategy_name[i]}'] * 31536000 / 1e18
        # supply_apy = borrow_apy * (1 - fee_to_protocol_rate / fee_precision ) * utilization_rate / 100
        output_data[f'supplyApy_{strategy_name[i]}'] = output_data[f'borrowApy_{strategy_name[i]}'] * (
                1 - df[f'feeToProtocolRate{strategy_name[i]}'] / 100000) * output_data[
                                                           f'utilization{strategy_name[i]}']
        output_data[f'spread{strategy_name[i]}'] = output_data[f'collateralApr_{strategy_name[i]}'] - output_data[
            f'borrowApy_{strategy_name[i]}']
        output_data[f'oracleLow{strategy_name[i]}'] = df[f'lowExchangeRate{strategy_name[i]}']
        output_data[f'oracleHigh{strategy_name[i]}'] = df[f'highExchangeRate{strategy_name[i]}']
        output_data[f'oracleNormalized{strategy_name[i]}'] = df[f'lowExchangeRate{strategy_name[i]}'] * df[
            f'pps{strategy_name[i]}'] / df[f'virtualPrice{strategy_name[i]}']
        output_data[f'maxLTV{strategy_name[i]}'] = df[f'maxLTV{strategy_name[i]}']

    return output_data


def load_data():
    save_strategy_data = pd.read_csv('sturdyDataStrategyV1.csv')
    save_pps_data = pd.read_csv('sturdyDataPpsV1.csv')
    address_log = pd.read_csv('address_log.csv')
    return save_strategy_data, save_pps_data, address_log


def get_data_for_blocks(historic_block_list, save_strategy_data, save_pps_data):
    new_strategy_data = merge_strategy_data(historic_block_list=historic_block_list)
    save_strategy_data = save_strategy_data.copy()
    save_strategy_data = pd.concat([save_strategy_data, new_strategy_data], ignore_index=True)
    save_strategy_data = save_strategy_data.sort_values(by='block')

    new_pps_data = merge_pps_data(historic_block_list_pps=historic_block_list)
    save_pps_data = save_pps_data.copy()
    save_pps_data = pd.concat([save_pps_data, new_pps_data], ignore_index=True)
    save_pps_data = save_pps_data.sort_values(by='block')

    save_data(save_strategy_data, save_pps_data)

    return save_strategy_data, save_pps_data


def save_data(save_strategy_data, save_pps_data):
    save_strategy_data.to_csv('sturdyDataStrategyV1.csv', index=False)
    save_pps_data.to_csv('sturdyDataPpsV1.csv', index=False)


# Function to convert block number to date
def block_number_to_date(block_number):
    try:
        # Get block information
        block = w3.eth.get_block(int(block_number))  # Convert block number to int

        # Check if block exists
        if not block:
            return

        # Convert timestamp to date
        timestamp = block.timestamp
        date = datetime.datetime.utcfromtimestamp(timestamp)

        return date  # Return the date object

    except Exception as e:
        print('Error:', e)
        return None


def generate_time_series(historic_block_list):
    # Initialize lists to store block numbers and corresponding times
    block_numbers = []
    times = []

    # Iterate over the historic_block_list
    for block_number in historic_block_list:
        # Call block_number_to_date function to get the time for each block number
        time = block_number_to_date(block_number)

        # Append block number and time to the lists
        block_numbers.append(block_number)
        times.append(time)

    # Create a DataFrame from the lists
    df = pd.DataFrame({'block': block_numbers, 'time': times})

    return df