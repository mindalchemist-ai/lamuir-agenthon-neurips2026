NumPy 2.5.3; SciPy 1.18.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: SciPy stats: distributions, tails and statistical tests

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
from scipy import stats
```

- Distribution methods `cdf(x,loc=0,scale=1)`, `sf(x,...)` and `ppf(q,...)` return scalars/ndarrays. sf directly evaluates the right tail and is more stable than 1-cdf. scale is a standard deviation or distribution scale, not a variance.
```python
z=stats.norm.ppf(.9); assert np.isclose(stats.norm.cdf(z),.9); assert stats.norm.sf(10)>0; assert np.isclose(stats.t.cdf(0,df=7),.5)
```
- `norm.logpdf(x,loc=0,scale=1)` returns a scalar/array. Sum logpdf values for likelihoods instead of multiplying many densities. `multivariate_normal(mean=None,cov=1,allow_singular=False)` returns a frozen distribution; covariance must be positive semidefinite. Set allow_singular only when the definition permits singularity.
```python
assert np.isfinite(stats.norm.logpdf([0.,1.],scale=2).sum()); mv=stats.multivariate_normal(mean=[0.,0.],cov=[[1.,.2],[.2,1.]]); assert np.isclose(mv.pdf([0.,0.]),1/(2*np.pi*np.sqrt(.96)))
```
- `rankdata(a,method='average',axis=None)` returns an ndarray, averaging tied ranks by default. `spearmanr(a,b=None,axis=0,nan_policy='propagate')` returns SignificanceResult with statistic/pvalue; it is not Pearson correlation of the original values.
```python
assert stats.rankdata([3,1,1]).tolist()==[3.,1.5,1.5]; assert np.isclose(stats.spearmanr([1,2,3],[4,6,8]).statistic,1.)
```
- `ttest_1samp(a,popmean,alternative='two-sided',nan_policy='propagate')` returns TtestResult for a mean test, using an independent-observation standard error by default; it does not replace HAC. `ttest_ind(a,b,equal_var=False)` is Welch's test.
```python
res=stats.ttest_1samp([1.,2.,4.,5.],0.,alternative='greater'); assert res.statistic>0 and 0<=res.pvalue<=1; assert np.isfinite(stats.ttest_ind([1,2,4],[2,4,7],equal_var=False).statistic)
```
- `genpareto.fit(data,floc=0)` returns (shape,loc,scale). Fit threshold excesses, not all unshifted losses. `genpareto.ppf(q,c,loc=0,scale=1)` returns conditional excess quantiles; converting to unconditional tail quantiles also requires the exceedance probability.
```python
sample=stats.genpareto.rvs(.15,size=300,random_state=np.random.default_rng(9)); shape,loc,scale=stats.genpareto.fit(sample,floc=0); assert loc==0 and scale>0 and np.isfinite(stats.genpareto.ppf(.9,shape,loc=loc,scale=scale))
```
- `qmc.Sobol(d,scramble=True,seed=...)` returns an engine. `random_base2(m)` returns a (2**m,d) ndarray; arbitrary sample counts can break balance. Handle 0/1 endpoints before applying an inverse normal CDF.
```python
u=stats.qmc.Sobol(d=2,scramble=True,seed=9).random_base2(4); assert u.shape==(16,2); assert np.isfinite(stats.norm.ppf(np.clip(u,np.finfo(float).eps,1-np.finfo(float).eps))).all()
```

## Additional explicitly named APIs

- `stats.norm.pdf(x,loc=0,scale=1)` returns a density scalar/ndarray. cdf is cumulative probability; pdf is not an interval probability. `stats.chi2.sf(x,df)`, `stats.f.sf(x,dfn,dfd)` and `stats.t.sf(x,df)` return right-tail probabilities. Symmetric two-sided t tests commonly use 2*t.sf(abs(tstat),df). Do not exchange numerator and denominator F degrees of freedom.
```python
assert np.isclose(stats.norm.pdf(0),1/np.sqrt(2*np.pi)); assert np.isclose(stats.chi2.sf(2.,df=2),np.exp(-1)); assert np.isclose(stats.f.sf(1.,dfn=5,dfd=5),.5); assert np.isclose(2*stats.t.sf(0.,df=9),1.)
```
- `stats.ncx2.pdf(x,df,nc,loc=0,scale=1)` returns a noncentral chi-square density. nc is the noncentrality parameter; scale rescales the variable. Variable transformations also require their Jacobian. `stats.multivariate_normal.cdf(x,mean=None,cov=1,allow_singular=False,*,rng=None,...)` returns a joint cumulative probability. Correlated marginals cannot simply be multiplied. Numerical integration can have random error; specify rng and error tolerances.
```python
assert np.allclose(stats.ncx2.pdf([.5,2.,5.],df=4,nc=0),stats.chi2.pdf([.5,2.,5.],df=4)); probability=stats.multivariate_normal.cdf([0.,0.],mean=[0.,0.],cov=[[1.,0.],[0.,1.]],rng=np.random.default_rng(33)); assert abs(probability-.25)<1e-8
```
- `stats.skew(a,axis=0,bias=True,nan_policy='propagate')` returns a scalar/array; the default bias=True is the moment estimator, bias=False the adjusted one (only when the task says unbiased, adjusted or sample-corrected). `stats.kurtosis(a,axis=0,fisher=True,bias=True,...)` defaults to excess kurtosis (normal=0); fisher=False gives ordinary kurtosis (normal=3). Specify bias correction and whether 3 is subtracted.
```python
sample=np.array([-3.,-1.,0.,1.,4.,6.]); assert np.isfinite(stats.skew(sample)); excess=stats.kurtosis(sample,fisher=True); ordinary=stats.kurtosis(sample,fisher=False); assert np.isclose(ordinary-excess,3.)
```
- `stats.kendalltau(x,y,nan_policy='propagate',method='auto',variant='b',alternative='two-sided')` returns SignificanceResult(statistic,pvalue). Default tau-b adjusts for ties; it is neither a simple untied-pair proportion nor Spearman rank correlation.
```python
result=stats.kendalltau([1.,2.,2.,4.],[1.,3.,3.,5.]); assert np.isclose(result.statistic,1.) and 0<=result.pvalue<=1
```
- `stats.t.fit(data,...)` returns (df,loc,scale), estimating all three by default. Use floc or fscale to fix location or scale. Student-t scale is not standard deviation: variance=scale**2*df/(df-2) when df>2; no finite variance exists for df<=2.
```python
draws=stats.t.rvs(df=8,loc=0,scale=1.2,size=450,random_state=np.random.default_rng(35)); degree,location,scale=stats.t.fit(draws,floc=0); assert degree>0 and location==0 and scale>0; assert np.isclose(stats.t.var(df=8,scale=1.2),1.2**2*8/6)
```
- `stats.gaussian_kde(dataset,bw_method=None,weights=None)` returns a callable KDE. Univariate data have shape (n,); multivariate data have shape (dimensions,samples). bw_method='silverman' selects this library's rule, not any arbitrary univariate heuristic with that name. `kde(points)` returns density ndarrays. `integrate_box_1d(low,high)` returns interval probability, not a tail first moment; the ES numerator requires integrating x*kde(x).
```python
kde=stats.gaussian_kde(np.array([-2.,-1.,-.2,.3,1.,2.,3.]),bw_method='silverman'); assert kde([0.,1.]).shape==(2,); assert np.isclose(kde.integrate_box_1d(-np.inf,np.inf),1.)
```
```python
from scipy.integrate import quad
threshold=.8; mass=kde.integrate_box_1d(threshold,np.inf); tail_moment,error=quad(lambda point:point*float(kde([point])[0]),threshold,np.inf); assert 0<mass<1 and tail_moment/mass>threshold
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
