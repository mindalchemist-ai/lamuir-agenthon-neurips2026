pandas 3.0.5; PyArrow 25.0.1; openpyxl 3.1.5 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Read typed local spreadsheet and columnar tables

read_excel(sheet_name=None) returns a sheet/DataFrame dict. openpyxl data_only reads cached formula values, not recalculation; missing caches can be None. Close workbooks. PyArrow read_table returns Table, then to_pandas; preserve_index=False avoids implicit index columns. For read_parquet inspect schema, timezones, nullable types and original row count before filtering. CSV date and numeric types require explicit parsing.

```python
import pandas as pd, pyarrow as pa, openpyxl
f=pd.DataFrame({'value':[2.,4.]}); t=pa.Table.from_pandas(f,preserve_index=False)
assert t.to_pandas().equals(f)
w=openpyxl.Workbook(); w.close()
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: Table.to_df -> Table.to_pandas.
