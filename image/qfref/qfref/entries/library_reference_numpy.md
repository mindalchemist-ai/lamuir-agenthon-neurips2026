NumPy 2.5.3 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: NumPy: arrays, grouped accumulation and numerical linear algebra

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
x=np.array([1.,2.,4.,8.]); A=np.array([[2.,1.],[1.,3.]])
```

- `asarray(a, dtype=None)` returns an ndarray with positional axes; converting a Series discards its labels. For two-dimensional matrices, `@` multiplies matrices and `*` multiplies elements.
- `mean(a, axis=None)` and `std(a, axis=None, ddof=0)` return a scalar or ndarray. The default population standard deviation uses ddof=0; request ddof=1 for a sample standard deviation. NaNs are not ignored automatically; use nanmean/nanstd explicitly when appropriate.
```python
assert np.asarray(x).shape == (4,); assert np.isclose(np.std(x,ddof=1)**2,np.var(x,ddof=1)); assert np.isnan(np.mean([1.,np.nan])); assert np.nanmean([1.,np.nan])==1.
```
- `quantile(a,q,method='linear')` returns a scalar/ndarray. Match the quantile algorithm to the definition; q is a probability, not a percentage.
```python
assert np.quantile(x,.5,method='linear')==3.; assert np.percentile(x,50)==3.
```
- `add.at(a, indices, b)` returns None and accumulates repeated indices in place, one occurrence at a time. Advanced indexing `a[idx] += b` does not reliably accumulate repeated locations. `bincount(x,weights=None,minlength=0)` returns a one-dimensional ndarray; group keys must be nonnegative integers.
```python
z=np.zeros(3); np.add.at(z,[0,0,2],[2.,3.,7.]); assert np.array_equal(z,np.bincount([0,0,2],weights=[2.,3.,7.],minlength=3))
```
- `linalg.solve(a,b)` returns an ndarray solving a square system; prefer it to an explicit inverse. `linalg.lstsq(a,b,rcond=None)` returns (coefficients, residual sum of squares, rank, singular values); the residual array can be empty. `linalg.pinv(a,rcond=...)` returns a pseudoinverse ndarray.
```python
b=np.array([1.,4.]); assert np.allclose(A@np.linalg.solve(A,b),b); coef,ss,rank,sv=np.linalg.lstsq(A,b,rcond=None); assert rank==2; assert np.allclose(np.linalg.pinv(A,rcond=1e-12)@b,coef)
```
- `linalg.matrix_power(a,n)` returns the integer matrix power as an ndarray; `a**n` is elementwise. `linalg.eigh(a)` returns ascending eigenvalues and corresponding eigenvectors in columns for a real symmetric matrix. Reverse the order when selecting the largest PCA components.
```python
assert np.allclose(np.linalg.matrix_power(A,3),A@A@A); val,vec=np.linalg.eigh(A); assert np.allclose(A@vec,vec*val); assert np.linalg.matrix_rank(A)==2
```
- `random.default_rng(seed)` returns a Generator. Keep the generator and draw order fixed; use `.normal(size=...)` or `.choice(...)` without relying on global random state.
```python
assert np.array_equal(np.random.default_rng(17).normal(size=4),np.random.default_rng(17).normal(size=4)); assert np.random.default_rng(17).choice([-1,1],size=(3,4)).shape==(3,4)
```
Do not mix simple and log returns. Near zero, `log1p` and `expm1` are more stable than adding/subtracting separately around log/exp.
```python
assert np.allclose(np.expm1(np.log1p(x/100)),x/100)
```

## Additional explicitly named APIs

- `np.linspace(start,stop,num=50,endpoint=True)` returns equally spaced points as an ndarray; num counts points, not step size. `np.ones(shape,dtype=float)` creates the requested shape. `np.column_stack(tup)` stacks one-dimensional inputs as columns; `np.vstack(tup)` stacks along the first axis. `np.append(arr,values,axis=None)` returns a new array and flattens by default; it is not an in-place list append.
```python
assert np.linspace(-2.,2.,5).tolist()==[-2.,-1.,0.,1.,2.]; assert np.ones((2,3)).shape==(2,3); assert np.column_stack([np.ones(4),np.arange(4)]).shape==(4,2); assert np.vstack([np.ones((1,3)),np.zeros((1,3))]).shape==(2,3); assert np.append([2,3],[5]).tolist()==[2,3,5]
```
- `np.median(a,axis=None)` returns a scalar/array and averages the two middle observations for an even sample size. `np.quantile(a,q,method='lower')` selects the observation at the lower quantile position; it is not interchangeable with default linear interpolation. `np.percentile(a,q,method='linear')` uses q in 0..100.
```python
assert np.median([1.,4.,7.,12.])==5.5; assert np.quantile([1.,4.,7.,12.],.5,method='lower')==4.; assert np.percentile([1.,4.,7.,12.],50,method='linear')==5.5
```
- `np.gradient(f,*varargs,axis=None,edge_order=1)` returns an ndarray for one-dimensional input, or a sequence of gradient arrays for multiple axes. Pass nonuniform coordinates through varargs. edge_order=2 uses a second-order boundary formula and requires at least three points on the axis. When two successive gradient calls are specified for a second derivative, use the same coordinates both times rather than substituting another stencil.
```python
coord=np.array([-2.,-.5,1.,3.]); values=coord**2; first=np.gradient(values,coord,edge_order=2); second=np.gradient(first,coord,edge_order=2); assert np.allclose(first,2*coord) and np.allclose(second,2.)
```
- `np.corrcoef(x,y=None,rowvar=True)` returns a correlation matrix. Variables occupy rows by default; use rowvar=False when samples occupy rows. Constant columns have undefined correlations. Dates and lagged observations are not aligned automatically. `np.dot(a,b)` contracts axes according to dimensionality; two-dimensional products can use @. `np.outer(a,b)` flattens inputs into an outer product, not an elementwise product.
```python
mat=np.column_stack([np.arange(6.),2*np.arange(6.)+3]); assert np.allclose(np.corrcoef(mat,rowvar=False),np.ones((2,2))); assert np.dot([1.,2.],[3.,4.])==11.; assert np.outer([2.,3.],[4.,5.]).shape==(2,2)
```
- `np.polynomial.legendre.leggauss(deg)` returns (nodes ndarray, weights ndarray) for integration on [-1,1]. Mapping to [a,b] requires rescaling both nodes and weights, not just moving the nodes.
```python
nodes,weights=np.polynomial.legendre.leggauss(16); lo,hi=-1.,2.; mapped=(hi-lo)*nodes/2+(hi+lo)/2; result=(hi-lo)/2*np.dot(weights,mapped**2); assert np.isclose(result,(hi**3-lo**3)/3)
```
- `np.random.seed(seed)` returns None and resets legacy global state. `np.random.RandomState(seed)` creates a separate legacy generator; `np.random.default_rng(seed)` creates a new Generator. Equal seeds do not make all three produce the same sequence. Preserve a specified legacy interface rather than replacing it with default_rng, and do not reset the seed before each draw.
```python
np.random.seed(29); legacy=np.random.normal(size=5); state=np.random.RandomState(29); assert np.array_equal(legacy,state.normal(size=5)); assert not np.array_equal(legacy,np.random.default_rng(29).normal(size=5))
```
- `np.cumsum(a,axis=None)` / `np.cumprod(a,axis=None)` return cumulative arrays. Simple-return wealth is cumprod(1+r); log-return wealth is exp(cumsum(r)). `np.prod` reduces the input; `np.maximum.accumulate` tracks the running maximum. `np.diag(v,k=0)` constructs a diagonal matrix from a vector or extracts a diagonal from a two-dimensional array.
```python
simple=np.array([.03,-.01,.02]); assert np.allclose(np.cumprod(1+simple),np.exp(np.cumsum(np.log1p(simple)))); assert np.isclose(np.prod(1+simple),np.cumprod(1+simple)[-1]); assert np.maximum.accumulate([2.,1.,4.]).tolist()==[2.,2.,4.]; assert np.diag(np.diag([2.,3.])).tolist()==[2.,3.]
```

## Version check: forms that fail in this version

### Removed or renamed forms
- np.math -> Python math.
- np.trapz -> np.trapezoid.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- ndarray.values -> the array itself.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
