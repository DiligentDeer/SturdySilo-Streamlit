import streamlit as st
# import plotly.graph_objs as go
# import pandas as pd
import utils
import charts
import const

# LOAD past saved files
saved_strategy_data, saved_pps_data, address_log = utils.load_data()

# Get the latest Block Number to check if enough time has passed to accumulate data for new Blocks
latest_block_with_data = saved_strategy_data['block'].max()

historic_block_list = utils.accumulate_block_with_no_data(latest_block_with_data)

latest_address_block = address_log['block'].max()

if int(latest_address_block) + 3600 < int(max(historic_block_list)):
    dune_usage = 1
    print(dune_usage)
    address_log = utils.update_and_save_address_list(loaded_address_log=address_log)
else:
    dune_usage = 0
    print(dune_usage)

if utils.w3.eth.block_number - const.BLOCK_INTERVAL > latest_block_with_data:
    saved_strategy_data, saved_pps_data = utils.get_data_for_blocks(historic_block_list, saved_strategy_data,
                                                                    saved_pps_data)

master_data = utils.compute_master_data(utils.process_dataframe(saved_pps_data), saved_strategy_data)

user_table = utils.compute_user_ltv(saved_strategy_data, address_log)

#### Testing
# user_table = pd.read_csv('user_tableV1.csv')
# print(user_table)
# master_data.info()
# user_table.info()
# user_table.to_csv('user_tableV1.csv', index=False)
#####

# Set the layout width to a wider size
st.set_page_config(layout="wide")

# Add title to your Streamlit app
st.title('Sturdy crvUSD Aggregator Silo Data')

for i in range(len(const.STRATEGY_NAME)):
    charts.instantaneous_data(master_data, const.STRATEGY_NAME[i])
    charts.usage_metrics(master_data, const.STRATEGY_NAME[i])
    charts.misc_charts(master_data, const.STRATEGY_NAME[i])

# Create two columns layout
left_column, right_column = st.columns(2)

charts.position_risk_chart(user_table, const.STRATEGY_NAME[0], left_column)
charts.position_risk_chart(user_table, const.STRATEGY_NAME[1], right_column)

charts.position_risk_chart(user_table, const.STRATEGY_NAME[2], left_column)
charts.position_risk_chart(user_table, const.STRATEGY_NAME[3], right_column)



charts.user_position_table(user_table, const.STRATEGY_NAME[0], left_column)
charts.user_position_table(user_table, const.STRATEGY_NAME[1], right_column)

charts.user_position_table(user_table, const.STRATEGY_NAME[2], left_column)
charts.user_position_table(user_table, const.STRATEGY_NAME[3], right_column)

st.markdown('<p class="center">A Dashboard by <a href="https://twitter.com/LlamaRisk">LlamaRisk</a>! Builder: <a href="https://twitter.com/diligentdeer">DiligentDeer</a>. Credits: <a href="https://twitter.com/0xValJohn">Val</a> & <a href="https://twitter.com/iamllanero">Llanero</a></p>', unsafe_allow_html=True)

st.markdown(f"""
Latest Block with Data: {latest_block_with_data}
Current Block: {max(historic_block_list)}
User Address from Block: {latest_address_block}
Dune Usage: {dune_usage}
""")
