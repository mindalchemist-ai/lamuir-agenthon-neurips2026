Matplotlib 3.11.1; Seaborn 0.13.2; Plotly 7.0.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Save static or interactive chart files

Use Agg before pyplot in headless environments. Save the intended Figure and close it. Seaborn lineplot aggregates repeated x and estimates intervals by default; raw series needs estimator=None,errorbar=None. Plotly write_html(include_plotlyjs=True) works offline; write_image needs extra rendering dependencies. Keep sampling and computation outside plotting.

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns, plotly.express as px
f,a=plt.subplots(); sns.lineplot(x=[0,1],y=[2,3],estimator=None,errorbar=None,ax=a)
assert len(a.lines)==1; plt.close(f); assert len(px.line(x=[0,1],y=[2,3]).data)==1
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
