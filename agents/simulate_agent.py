import os
import math
import numpy as np
import pandas as pd
from config import constants
from utils import io_utils
from sklearn.linear_model import LogisticRegression

"""
Simulate Agent to run historic backtesting using model
Agent weights and CBR model are generated
Tradebook is saved
"""
class SimulateAgent():

    def __init__(self, alpha=0.05):

        # Define agent names
        self.signal_agent_names = ['SentimentAgent', 'MAAgent', 'BollingerAgent', 'RSIAgent']
        self.macro_var = ['MACRO_0','MACRO_1','MACRO_2', 'VaR']

        # Load Historical Data
        self.data = pd.read_csv(os.path.join(constants.DATA_DIR, 'IS5006_Historical.csv'), index_col='datetime', parse_dates=[0], dayfirst=True)
        self.data['VaR'] = self.data['VaR'].pct_change()
        self.data['VaR'].fillna(0.0, inplace=True)
        
        # Initialise weights, CBR and equity portfolio
        self.agent_weights = [1.0/len(self.signal_agent_names)]*len(self.signal_agent_names)
        self.cbr = LogisticRegression(solver='liblinear')
        self.crypto = 0.0
        self.quantity = constants.QUANTITY
        self.capital = constants.START_CAPITAL
        self.alpha = alpha # Learning rate
        self.pnl = []
        self.tradebook = pd.DataFrame(columns=['Action', 'Quantity', 'Price', 'Balance', 'PNL']+sorted(self.signal_agent_names)+self.macro_var)

    """
    Run simulation over historic periods
    Simulate buy/sell action by updating dataframe
    Train and use CBR and agent weights for each trade
    """
    def simulate(self):

        # Iterate over dataframe rows
        for index, row in self.data.iterrows():
            dir = 0

            # Generate combined trade signal
            agent_signals = row[self.signal_agent_names].to_list()
            agent_signal = np.sum(np.dot(agent_signals, self.agent_weights))
            
            prev_rows = self.data[self.data.index < index]
            temp_capital = self.capital
            temp_crypto = self.crypto

            # Simulate trade based on signal
            if(agent_signal > 0):
                if(self.capital >= self.quantity*row['Close']):
                    self.data.loc[index, 'Action'] = 'buy'
                    self.data.loc[index, 'Quantity'] = self.quantity
                    self.data.loc[index, 'Price'] = row['Close']
                    temp_capital = self.capital - (self.quantity * row['Close'])
                    temp_crypto = self.crypto + self.quantity
                    self.data.loc[index, 'Balance'] = temp_capital

                    # Run CBR if enough trades for learning algorithm
                    if(len(self.tradebook) > 20):
                        dir = self._run_cbr(self.data.loc[index])

                    #Reupdate quantity based on CBR
                    self.data.loc[index, 'Quantity'] = round((1.0-(float(dir)*constants.LEARNING_RATE))*self.quantity, 2)
                    temp_capital = self.capital - (self.data.loc[index, 'Quantity'] * row['Close'])
                    temp_crypto = self.crypto + self.data.loc[index, 'Quantity']
                    self.data.loc[index, 'Balance'] = temp_capital

                    self.capital = temp_capital
                    self.crypto = temp_crypto
                    self._update_tradebook(index, self.data.loc[index], prev_rows)
                else:
                    pass
            elif(agent_signal < 0):
                if(self.crypto > 0):
                    self.data.loc[index, 'Action'] = 'sell'
                    self.data.loc[index, 'Quantity'] = self.crypto
                    self.data.loc[index, 'Price'] = row['Close']
                    self.capital = self.capital + (self.crypto * row['Close'])
                    self.crypto = 0.0
                    self.data.loc[index, 'Balance'] = self.capital

                    self._evaluate(self.data.loc[index], prev_rows)
                    self._update_tradebook(index, self.data.loc[index], prev_rows)
                else:
                    pass
            else:
                continue
        print(f'Final PnL: {sum(self.pnl)}, Capital: {self.capital}, Crypto: {self.crypto} @ Price {self.data.iloc[-1]["Close"]}')
        print(f'Agent Weights: {self.agent_weights}')
        print(f'# Trades {len(self.tradebook)}')

        # Update final PnL for uncompleted trades (buys with no matching sell)
        for index, row in self.tradebook.iterrows():
            if(math.isnan(row['PNL'])):
                self.tradebook.loc[index:, 'PNL'] = (self.data.iloc[-1]["Close"] - row['Price'])*row['Quantity']
        self._save_data()

    """
    Evaluate PNL for each trade
    Update agent weights"""
    def _evaluate(self, sell_row, prev_rows):

        # Calculate average buy price, buy quantity, sell price, sell quantity
        buy_rows = prev_rows[prev_rows['Action'] == 'buy'].iloc[-int(round(sell_row['Quantity'])):]
        buy_quantity = buy_rows['Quantity'].sum()
        buy_price = (buy_rows['Price']*buy_rows['Quantity']).sum()/buy_quantity

        # Calculate and update PNL
        pnl = (sell_row['Price']*sell_row['Quantity']) - (buy_price*buy_quantity)
        self.pnl.append(pnl)
        print(f'Capital: {self.capital} PnL: {pnl}; selling {sell_row["Quantity"]} @ {sell_row["Price"]} & buying {buy_quantity} @ {buy_price}')
        
        # Update weights depending on whether profit or loss for given trades
        if(pnl < 0):
            sell_signals = sell_row[self.signal_agent_names].to_list()
            buy_signals = buy_rows[self.signal_agent_names].sum().to_list()
            self.agent_weights = np.add(self.agent_weights, np.subtract(self._scalar_mult(sell_signals), self._scalar_mult(buy_signals)))
        elif(pnl > 0):
            sell_signals = sell_row[self.signal_agent_names].to_list()
            buy_signals = buy_rows[self.signal_agent_names].sum().to_list()
            self.agent_weights = np.subtract(self.agent_weights, np.subtract(self._scalar_mult(sell_signals), self._scalar_mult(buy_signals)))

    """Function to facilitate scalar multiplication"""
    def _scalar_mult(self, signals):
        return([x*self.alpha for x in signals])

    """Update row in tradebook dataframe with data necessary for CBR"""
    def _update_tradebook(self, index, row, prev_rows):

        # Update data in tradebook along with PnL for closed trades
        if(row['Action'] == 'buy'):
            self.tradebook.loc[index] = [row['Action'], row['Quantity'], row['Price'], row['Balance'], np.NaN] + row[self.signal_agent_names].to_list() + row[self.macro_var].to_list()
        else:
            buy_rows = prev_rows[prev_rows['Action'] == 'buy'].iloc[-int(round(row['Quantity'])):]
            buy_quantity = buy_rows['Quantity'].sum()
            buy_price = (buy_rows['Price']*buy_rows['Quantity']).sum()/buy_quantity
            pnl = (row['Price']*row['Quantity']) - (buy_price*buy_quantity)
            for ix in buy_rows.index.to_list():
                self.tradebook.loc[ix, 'PNL'] = pnl

            # Add columns useful for CBR
            self.tradebook.loc[index] = [row['Action'], row['Quantity'], row['Price'], row['Balance'], pnl] + row[self.signal_agent_names].to_list() + row[self.macro_var].to_list()

    """Save weights, tradebook and CBR model to csv"""
    def _save_data(self):
        io_utils.df_to_csv(self.tradebook, os.path.join(constants.DATA_DIR, 'tradebook.csv'))
        io_utils.save_pickle(self.cbr, os.path.join(constants.DATA_DIR, 'cbr.pkl'))
        agent_weights_df = pd.DataFrame(columns=self.signal_agent_names)
        agent_weights_df.loc[0] = self.agent_weights
        io_utils.df_to_csv(agent_weights_df, os.path.join(constants.DATA_DIR, 'agent_weights.csv'))

    """Run CBR model on trades upto current trade to predict direction of PNL"""
    def _run_cbr(self, row):

        # Get completed trades
        last_non_nan = self.tradebook['PNL'].last_valid_index()
        
        # Form train test split
        X, y = self.tradebook.loc[:last_non_nan, self.tradebook.columns != 'PNL'].copy(), self.tradebook.loc[:last_non_nan, 'PNL'].copy()
        X.loc[:, 'Action'] = X['Action'].apply(lambda x: 1 if 'buy' else -1)
        y = np.where(y > 0, 1, -1)

        # Fit and Predict
        self.cbr.fit(X, y)
        pred_row = pd.DataFrame(row).T
        pred_row.loc[:, 'Action'] = pred_row['Action'].apply(lambda x: 1 if 'buy' else -1)
        pred_row.drop(['Open', 'High', 'Low', 'Close', 'Volume'], inplace = True, axis=1)
        pred_pnl = self.cbr.predict(pred_row)
        return(pred_pnl[0])