import pandas as pd
from pathlib import Path
 
#edit to change
csv = "/Users/vince/Downloads/45.csv"
clustercol = "Heater_Status" #column to display for clusters (1)
tempcol = "Temp_C" #column to display for clusters(2)
nstep = 5 #measured every 5s so 5 increment
outputfile = "clusters45.txt" 


outputfile = Path.home() / "Downloads" / outputfile
 
df = pd.read_csv(csv)

group_ids = (df[clustercol] != df[clustercol].shift()).cumsum()

lines = []
for i, (_, cluster) in enumerate(df.groupby(group_ids), start=1):
    lines.append(f"CLUSTER {i}" + "-" * 20)
    for idx, (_, row) in enumerate(cluster.iterrows(), start=0):
        n = idx * nstep
        lines.append(f"{n} {row[tempcol]}")
    lines.append("")
 
outputfile.write_text("\n".join(lines))
print(f"saved: {outputfile}")
 

