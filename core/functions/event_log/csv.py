import logging

from pandas import read_csv, DataFrame

# Enable logging
logger = logging.getLogger("prcore")


def get_dataframe_from_csv(path: str, seperator: str) -> DataFrame:
    # Get dataframe from csv file
    df = read_csv(path, sep=seperator, dtype=str)
    df_obj = df.select_dtypes(['object'])
    df[df_obj.columns] = df_obj.apply(lambda x: x.str.strip())
    return df
