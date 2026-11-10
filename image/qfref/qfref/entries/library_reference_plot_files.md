NumPy 2.5.3; pandas 3.0.5; Matplotlib 3.11.1; Seaborn 0.13.2; Plotly 7.0.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: Matplotlib, Seaborn and Plotly: files only when requested

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
folder=Path(tempfile.mkdtemp()); frame=pd.DataFrame({'time':[0,1,2],'value':[1.,1.2,1.1]})
```

- `plt.subplots(nrows=1,ncols=1,figsize=None)` returns (Figure,Axes); Axes can be an ndarray for multiple subplots. `ax.plot(x,y)` returns a list of Line2D objects. `fig.savefig(fname,dpi=...,bbox_inches='tight')` returns None; `plt.close(fig)` releases the figure. In headless environments, set Agg before importing pyplot.
```python
fig,ax=plt.subplots(figsize=(5,3)); lines=ax.plot(frame['time'],frame['value']); ax.set(xlabel='Time',ylabel='Value'); fig.savefig(folder/'line.png',dpi=120,bbox_inches='tight'); plt.close(fig); assert len(lines)==1 and (folder/'line.png').stat().st_size>0
```
- `sns.lineplot(data=...,x=...,y=...,estimator='mean',errorbar=('ci',95),ax=None)` returns Axes. It aggregates repeated x values and estimates intervals by default; use estimator=None,errorbar=None for a raw time series. `sns.heatmap(data,ax=None)` returns Axes; label color-scale units.
```python
fig,ax=plt.subplots(); result=sns.lineplot(data=frame,x='time',y='value',estimator=None,errorbar=None,ax=ax); fig.savefig(folder/'series.png'); plt.close(fig); assert result is ax and (folder/'series.png').exists()
```
- `px.line(data_frame,x=None,y=None)` returns a Plotly Figure. `fig.write_html(file,include_plotlyjs=True,full_html=True)` returns None; embed JavaScript for offline viewing. Interactive HTML is not PNG. Static write_image needs additional rendering dependencies and must not be assumed available.
```python
plot=px.line(frame,x='time',y='value'); plot.write_html(folder/'interactive.html',include_plotlyjs=True,full_html=True); assert (folder/'interactive.html').stat().st_size>1000
```
Use these only when chart files are requested, with the required paths and formats. Finish computations before plotting; do not redraw random samples or alter data inside a save operation.

## Version check: forms that fail in this version

### Removed or renamed forms
- fillna(method=...) -> ffill()/bfill().
- to_numeric(errors='ignore') -> errors='raise' or 'coerce'; handle invalid values explicitly.
- np.math -> Python math.
- groupby(axis=1) -> df.T.groupby(...).agg(...).T; check dtypes.
- resample('M') -> resample('ME'); to_period('M') still uses M.
- resample('Q') -> resample('QE').
- resample('Y') -> resample('YE').
- DataFrame.applymap -> DataFrame.map.
- np.trapz -> np.trapezoid.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- pd.random -> the specified NumPy RNG interface.
- s.get_loc(label) -> s.index.get_loc(label).
- Series.to_series() -> omit it, or copy(); Index.to_series is valid.
- expanding().shift(...) -> aggregate before shift; ordering follows the definition.
- string Series.dt -> to_datetime(series).dt.
- ndarray.values -> the array itself.
- DatetimeIndex.dt.year -> index.year.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).
- PeriodIndex.dt.year -> index.year.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
