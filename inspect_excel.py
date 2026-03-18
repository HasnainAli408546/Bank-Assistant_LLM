# 
import pandas as pd

file = "NUST Bank-Product-Knowledge.xlsx"

df = pd.read_excel(file, sheet_name="PLS", header=None)

print(df.head(20))