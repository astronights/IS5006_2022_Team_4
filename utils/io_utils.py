import pickle
import pandas as pd
import pyarrow as pa
import pyarrow.csv as csv
from enum import Enum

class Type(Enum):
    AGENT_WEIGHTS = 'agent_weights.csv'
    ACCOUNT_BOOK = 'account_book.csv'

def df_to_csv(df, filename):
    if("Created_at" in df.columns):
        df['Created_at'] = df['Created_at'].astype('datetime64[ns]')
    if("Updated_at" in df.columns):
        df['Updated_at'] = df['Updated_at'].astype('datetime64[ns]')
    df_pa_table = pa.Table.from_pandas(df, preserve_index=False)
    csv.write_csv(df_pa_table, filename)

def csv_to_df(filename):
    df_pa_table = csv.read_csv(filename)
    df = df_pa_table.to_pandas()
    return df

def load_pickle(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

def save_pickle(obj, filename):
    with open(filename, 'wb') as f:
        pickle.dump(obj, f)