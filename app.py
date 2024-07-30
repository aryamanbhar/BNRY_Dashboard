import requests
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import logging
from flask import Flask, render_template_string
from datetime import datetime

# Initialize Flask app
server = Flask(__name__)

# Initialize Dash app
app = dash.Dash(__name__, server=server, url_base_pathname='/dash/')

# Optimism Etherscan API key, wallet address, mexC & bingX addresses
api_key = '67MWWUIVSIMV7MUY22TQBN51WAQINEVT13'
wallet_address = '0xB900908D7C186baaD357816E5fB67986123d2279'
mexc_address = '0xdf90c9b995a3b10a5b8570a47101e6c6a29eb945'
bingx_address = '0x6c69fa64EC451b1Bc5b5FBAa56CF648a281634Be'

#example wallet addresses
wallet_address_13 = '0xabccfeDdB92Ae3fd4658B7a0F6B2Da88bB67712E'
wallet_address_20 = '0xC759633a209673193E18D667DE2597E2F205aAaB'

initialTransactions = []
localHost = 'http://127.0.0.1:5000/'

# Global variable to store messages
fetch_messages = []
fetching_in_progress = False

def get_transactions(wallet_address, collected_data=None):
    global fetch_messages

    if collected_data is None:
        collected_data = []

    url = f'https://api-optimistic.etherscan.io/api?module=account&action=tokentx&address={wallet_address}&startblock=0&endblock=99999999&sort=asc&apikey={api_key}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        transactions = data.get('result', [])
        
        simplified_transactions = {}
        for tx in transactions:
            address = tx['to']
            amount = float(tx['value']) / 1e18  # Convert from wei to ether
            timestamp = datetime.fromtimestamp(int(tx['timeStamp'])).date()
            
            if address in simplified_transactions:
                simplified_transactions[address].append({'amount': amount, 'timestamp': timestamp})
            else:
                simplified_transactions[address] = [{'amount': amount, 'timestamp': timestamp}]
        
        # Collect data in a list for easy display in Dash
        for address, tx_list in simplified_transactions.items():
            collected_data.append({
                'address': address,
                'transactions': tx_list
            })
            if address == mexc_address:
                collected_data.append({'address': 'MexC reached', 'transactions': []})
                return collected_data
            if address == bingx_address:
                collected_data.append({'address': 'BingX reached', 'transactions': []})
                return collected_data

        # Get the first address
        all_addresses = list(simplified_transactions.keys())
        if all_addresses:
            initialTransactions.append(all_addresses[0])

        # Skip the first address and process the rest
        if len(all_addresses) > 1:
            next_address = all_addresses[1]
            fetch_messages.append(f"Fetching transactions from new address: {next_address}")
        
            collected_data.append({'address': f'{next_address} transactions below', 'transactions': []})
            return get_transactions(next_address, collected_data)
        
        fetching_in_progress = False
        return collected_data
    
    except requests.RequestException as e:
        logging.error(f"Error fetching transactions: {e}")
        return collected_data
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return collected_data

# Dash layout
app.layout = html.Div([
    dcc.Input(id='wallet-address', type='text', value=wallet_address, style={'width': '50%'}),
    html.Button('Submit', id='submit-button', n_clicks=0),
    dcc.Loading(
        id="loading-icon",
        type="circle",
        children=[
            html.Div(id='transactions-output'),
            html.Div(id='fetch-messages', style={'margin-top': '20px', 'color': 'blue'})
        ]
    )
])

# Dash callback to update graph and fetch messages
@app.callback(
    [Output('transactions-output', 'children'), Output('fetch-messages', 'children')],
    [Input('submit-button', 'n_clicks')],
    [State('wallet-address', 'value')]
)
def update_transactions_output(n_clicks, wallet_address):
    global fetch_messages

    if n_clicks == 0:
        return "", ""

    fetch_messages = []
    transactions = get_transactions(wallet_address)
    
    if not transactions:
        return "No transactions found.", ""

    children = []
    
    last_was_arrow = False
    for entry in transactions:
        address = entry['address']
        tx_list = entry['transactions']
        
        if last_was_arrow:
            last_was_arrow = False
            continue
        

        # If an address has empty transactions, style it in red
        if not tx_list and address != 'MexC reached':
            style = {'border': '1px solid black', 'padding': '10px', 'margin': '10px', 'background-color': 'red'}
            arrow = html.Div('↓', style={'font-size': '24px', 'text-align': 'center'})
            last_was_arrow = True  # Set the flag
        elif address == 'MexC reached':
            style = {'border': '1px solid black', 'padding': '10px', 'margin': '10px', 'background-color': 'red'}
            last_was_arrow = False
        else:
            style = {'border': '1px solid black', 'padding': '10px', 'margin': '10px'}
            arrow = None
            last_was_arrow = False  # Reset the flag
        
        address_box = html.Div([
            html.H4(f"Address: {address}"),
            html.Ul([html.Li(f"Amount: {tx['amount']}, Timestamp: {tx['timestamp']}") for tx in tx_list])
        ], style=style)
        

        children.append(address_box)
        if arrow:
            children.append(arrow)
        
    
    return children, html.Ul([html.Li(msg) for msg in fetch_messages])

@server.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Transaction Visualization</title>
    </head>
    <body>
        <h1>Transaction Visualization</h1>
        <div>
            <a href="/dash/">Go to Dash</a>
        </div>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    server.run(debug=True)
