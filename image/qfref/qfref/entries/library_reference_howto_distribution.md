NumPy 2.5.3; SciPy 1.18.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Fit distributions and evaluate tail probabilities

t.fit returns (df,loc,scale), not (loc,scale,df); scale is not standard deviation. ppf(q) inverts a lower-tail probability, isf(p) an upper-tail probability. Use sf instead of 1-cdf for small right tails; sum logpdf for likelihoods. GPD fits threshold excesses with floc=0. Set skew/kurtosis bias/fisher; Kendall and Spearman return statistic/pvalue. KDE orientation/bandwidth and tail first-moment integrals must be explicit.

```python
from scipy import stats
import numpy as np
assert np.isclose(stats.t.isf(.07,df=9),stats.t.ppf(.93,df=9))
assert stats.norm.sf(11)>0
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
