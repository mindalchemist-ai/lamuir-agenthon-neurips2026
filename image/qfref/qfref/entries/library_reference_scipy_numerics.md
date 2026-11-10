NumPy 2.5.3; SciPy 1.18.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: SciPy: matrix functions, integration and interpolation

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
from scipy import linalg, integrate, interpolate
A=np.array([[2.,.3],[.3,1.]])
```

- `linalg.expm(A)` returns a matrix exponential ndarray, for example from a generator to a transition matrix; it is neither elementwise exp nor an integer matrix power. `linalg.cholesky(a,lower=False)` returns a triangular ndarray, upper triangular by default. For simulation, use lower=True so L@L.T equals covariance.
```python
Q=np.array([[-.2,.2],[.1,-.1]]); P=linalg.expm(Q*2); assert np.allclose(P.sum(axis=1),1) and np.all(P>=0); L=linalg.cholesky(A,lower=True); assert np.allclose(L@L.T,A)
```
- `solve_banded((l,u),ab,b)` returns an ndarray. Store ab[u+i-j,j]=a[i,j]; do not pass an ordinary dense matrix as ab.
```python
ab=np.array([[0.,-1.,-1.],[2.,2.,2.],[-1.,-1.,0.]]); ans=linalg.solve_banded((1,1),ab,[1.,0.,1.]); assert np.allclose(ans,[1.,1.,1.])
```
- `integrate.quad(func,a,b,epsabs=...,epsrel=...,limit=...)` returns (integral, estimated error), not a strict error bound. Check warnings and truncation stability for oscillatory or infinite integrals. `trapezoid(y,x=None,dx=1,axis=-1)` returns a scalar/ndarray, integrating in the supplied x order without sorting. Avoid obsolete trapz calls.
```python
value,error=integrate.quad(lambda t:np.exp(-t),0,np.inf,epsabs=1e-10); assert abs(value-1)<1e-9 and error<1e-7; assert integrate.trapezoid([0.,1.,2.],x=[0.,1.,2.])==2.
```
- `solve_ivp(fun,t_span,y0,method='RK45',t_eval=None,rtol=...,atol=...)` returns OdeResult with y shaped (states,times). Check success.
```python
sol=integrate.solve_ivp(lambda t,y:-y,(0.,1.),[1.],t_eval=[0.,1.],rtol=1e-9,atol=1e-11); assert sol.success and abs(sol.y[0,-1]-np.exp(-1))<1e-8
```
- `PchipInterpolator(x,y,extrapolate=...)` returns a callable preserving monotone shape. `CubicSpline(x,y,bc_type='not-a-knot',extrapolate=...)` returns a callable spline. x must be strictly increasing without duplicates; specify boundary conditions and extrapolation.
```python
x=np.array([0.,1.,2.,3.]); y=np.array([0.,1.,1.5,2.]); f=interpolate.PchipInterpolator(x,y,extrapolate=False); assert np.allclose(f(x),y) and np.isnan(f(4)); g=interpolate.CubicSpline(x,y,bc_type='natural',extrapolate=False); assert np.allclose(g(x),y)
```

## Additional explicitly named APIs

- `scipy.linalg.logm(A)` returns a matrix logarithm ndarray, locally inverse to expm rather than elementwise log. It can be complex: check validity, imaginary magnitude and expm(logA) reconstruction error before taking .real. Dividing a transition matrix's logarithm by time does not ensure a valid generator; off-diagonals must be nonnegative and rows sum to zero. Apply constraints separately according to the definition. This version does not rely on the old disp argument.
```python
transition=np.array([[.85,.15],[.25,.75]]); logarithm=linalg.logm(transition); assert np.allclose(linalg.expm(logarithm),transition,rtol=1e-10,atol=1e-12); assert np.max(np.abs(np.imag(logarithm)))<1e-10
```

## Version check: forms that fail in this version

### Removed or renamed forms
- np.math -> Python math.
- np.trapz -> np.trapezoid.
- scipy.integrate.trapz -> scipy.integrate.trapezoid.
- logm(A,disp=False) -> logm(A); check expm reconstruction yourself.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- ndarray.values -> the array itself.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
