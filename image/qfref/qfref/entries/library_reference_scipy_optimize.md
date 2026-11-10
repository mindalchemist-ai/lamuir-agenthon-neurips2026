NumPy 2.5.3; SciPy 1.18.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: SciPy optimize: roots, least squares and constrained optimization

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
from scipy import optimize
```

- `brentq(f,a,b,xtol=...,rtol=...,full_output=False)` returns a root scalar, or (root,RootResults) with full_output=True. A continuous function needs opposite endpoint signs or an endpoint root. Check the bracket; do not return an initial guess after failure.
```python
root,info=optimize.brentq(lambda z:z*z-3,0.,3.,xtol=1e-12,full_output=True); assert info.converged and abs(root*root-3)<1e-10
```
- `root(fun,x0,method='hybr')` returns OptimizeResult. Inspect success, message and residuals, not only x.
```python
sol=optimize.root(lambda v:np.array([v[0]+v[1]-3,v[0]-v[1]-1]),[0.,0.]); assert sol.success and np.linalg.norm(sol.fun)<1e-9
```
- `minimize(fun,x0,method=None,bounds=None,constraints=(),options=None)` returns OptimizeResult. SLSQP dictionary inequalities mean fun(x)>=0. Check both tolerances and feasibility.
```python
fit=optimize.minimize(lambda v:float(v@v),[.4,.6],method='SLSQP',bounds=[(0,1)]*2,constraints={'type':'eq','fun':lambda v:v.sum()-1},options={'ftol':1e-12}); assert fit.success and abs(fit.x.sum()-1)<1e-9 and np.all(fit.x>=0)
```
- `least_squares(fun,x0,bounds=(-inf,inf),loss='linear')` returns OptimizeResult. fun supplies a residual vector; with linear loss, cost is half the sum of squared residuals. x0 must satisfy bounds. `curve_fit(f,xdata,ydata,p0=None,bounds=...)` returns (parameter ndarray, covariance ndarray); covariance is not the optimization objective.
```python
fit=optimize.least_squares(lambda v:np.array([v[0]-2,2*v[0]-4]),[1.],bounds=(0,np.inf)); assert fit.success and fit.cost<1e-15; par,cov=optimize.curve_fit(lambda t,a,b:a+b*t,np.arange(5.),1+2*np.arange(5.),p0=[0.,0.]); assert np.allclose(par,[1,2]) and cov.shape==(2,2)
```
- `linprog(c,A_ub=None,b_ub=None,A_eq=None,b_eq=None,bounds=(0,None),method='highs')` returns OptimizeResult. A_ub x <= b_ub and variables are nonnegative by default; change bounds explicitly to allow negatives. Construct scenario auxiliaries and weight constraints from the specified CVaR definition.
```python
lp=optimize.linprog([1.,2.],A_eq=[[1.,1.]],b_eq=[1.],bounds=[(0,None)]*2,method='highs'); assert lp.success and np.allclose(lp.x,[1,0])
```

## Additional explicitly named APIs

- `minimize(...,method='L-BFGS-B',bounds=...,options=...)` returns OptimizeResult and supports box constraints only; do not expect general nonlinear constraints to take effect. A local optimum is not necessarily global. Fit each starting point separately, check feasibility and success, then compare objective values.
```python
starts=[np.array([.2]),np.array([1.3]),np.array([2.8])]; fits=[optimize.minimize(lambda v:float((v[0]-1.7)**2),start,method='L-BFGS-B',bounds=[(0.,3.)]) for start in starts]; valid=[f for f in fits if f.success and np.isfinite(f.fun)]; best=min(valid,key=lambda f:f.fun); assert abs(best.x[0]-1.7)<1e-5
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
