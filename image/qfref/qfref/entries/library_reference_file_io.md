pandas 3.0.5; openpyxl 3.1.5; PyArrow 25.0.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: openpyxl and PyArrow: spreadsheet and columnar file I/O

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
from pathlib import Path
import tempfile
import pandas as pd
import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq
folder=Path(tempfile.mkdtemp())
```

- `openpyxl.load_workbook(filename,read_only=False,data_only=False)` returns Workbook. data_only=True reads cached formula results; it does not calculate formulas, and absent caches may yield None. `iter_rows(values_only=True)` yields tuples; `.close()` releases the file.
```python
book=openpyxl.Workbook(); sheet=book.active; sheet.append(['kind','amount']); sheet.append(['sample',2.5]); book.save(folder/'sample.xlsx'); book.close(); loaded=openpyxl.load_workbook(folder/'sample.xlsx',read_only=True,data_only=True); rows=list(loaded.active.iter_rows(values_only=True)); loaded.close(); assert rows[1]==('sample',2.5)
```
- `pd.read_excel(io,sheet_name=0,header=0,engine='openpyxl')` returns DataFrame; sheet_name=None returns dict[str,DataFrame]. Check headers, sheet names and date types first. Use ExcelWriter to manage write handles.
```python
frame=pd.read_excel(folder/'sample.xlsx',engine='openpyxl'); assert frame['amount'].iloc[0]==2.5; frame.to_excel(folder/'copy.xlsx',index=False,engine='openpyxl'); assert (folder/'copy.xlsx').stat().st_size>0
```
- `pa.Table.from_pandas(df,preserve_index=False)` returns Table. `pq.write_table(table,where,compression='snappy')` returns None; `pq.read_table(source,columns=None)` returns Table; `.to_pandas()` returns DataFrame. Explicitly decide whether to preserve the pandas index; check partition columns, timezones and nullable dtypes against the schema after reading.
```python
table=pa.Table.from_pandas(frame,preserve_index=False); pq.write_table(table,folder/'sample.parquet',compression='snappy'); restored=pq.read_table(folder/'sample.parquet',columns=['amount']).to_pandas(); assert restored['amount'].iloc[0]==2.5
```
- `DataFrame.to_parquet(path,index=False,engine='pyarrow')` returns None; `pd.read_parquet(path,columns=...,engine='pyarrow')` returns DataFrame. These examples use local files without remote filesystems.
```python
frame.to_parquet(folder/'copy.parquet',index=False,engine='pyarrow'); assert pd.read_parquet(folder/'copy.parquet',engine='pyarrow').equals(frame)
```

## Version check: forms that fail in this version

### Removed or renamed forms
- fillna(method=...) -> ffill()/bfill().
- to_numeric(errors='ignore') -> errors='raise' or 'coerce'; handle invalid values explicitly.
- groupby(axis=1) -> df.T.groupby(...).agg(...).T; check dtypes.
- resample('M') -> resample('ME'); to_period('M') still uses M.
- resample('Q') -> resample('QE').
- resample('Y') -> resample('YE').
- DataFrame.applymap -> DataFrame.map.

### Unavailable or wrong-object forms
- pd.random -> the specified NumPy RNG interface.
- s.get_loc(label) -> s.index.get_loc(label).
- Series.to_series() -> omit it, or copy(); Index.to_series is valid.
- expanding().shift(...) -> aggregate before shift; ordering follows the definition.
- string Series.dt -> to_datetime(series).dt.
- DatetimeIndex.dt.year -> index.year.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).
- PeriodIndex.dt.year -> index.year.
- Table.to_df -> Table.to_pandas.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
