
def chunk_dataframe(df, chunk_size):
    for start in range(0, len(df), chunk_size):
        yield df.iloc[start:start + chunk_size]