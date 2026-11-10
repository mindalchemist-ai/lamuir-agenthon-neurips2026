NumPy 2.5.3 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Resample, permute and compare refitted statistics

For fixed design/sample/weights, compute P=pinv(X) once and refit responses by Y@P.T. Recompute standard errors for t statistics. Count ties using abs(stat)>=abs(observed)-tol, with scale-aware tolerance; include the identity. Full enumeration uses its direct proportion; sampled tests may require (1+count)/(B+1). Restricted fits and exchangeability follow the test. Halve signs only after proving global-sign invariance.

```python
import numpy as np
X=np.column_stack([np.ones(6),np.arange(6.)]); y=np.array([1.,3.,2.,5.,4.,8.])
P=np.linalg.pinv(X); observed=(P@y)[1]; Y=np.stack([y,y+.2]); stat=(Y@P.T)[:,1]
tol=1e-12*max(1.,abs(observed)); assert (abs(stat)>=abs(observed)-tol)[0]
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
