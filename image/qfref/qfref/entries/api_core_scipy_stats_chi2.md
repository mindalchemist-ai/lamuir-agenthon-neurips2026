# Official API description: scipy.stats.chi2 (scipy 1.18.1)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
scipy.stats.chi2(*args, **kwds)

A chi-squared continuous random variable.

For the noncentral chi-square distribution, see `ncx2`.

As an instance of the `rv_continuous` class, `chi2` object inherits from it
a collection of generic methods (see below for the full list),
and completes them with details specific for this particular distribution.

Methods
-------
rvs(df, loc=0, scale=1, size=1, random_state=None)
    Random variates.
pdf(x, df, loc=0, scale=1)
    Probability density function.
logpdf(x, df, loc=0, scale=1)
    Log of the probability density function.
cdf(x, df, loc=0, scale=1)
    Cumulative distribution function.
logcdf(x, df, loc=0, scale=1)
    Log of the cumulative distribution function.
sf(x, df, loc=0, scale=1)
    Survival function  (also defined as ``1 - cdf``, but `sf` is sometimes more accurate).
logsf(x, df, loc=0, scale=1)
    Log of the survival function.
ppf(q, df, loc=0, scale=1)
    Percent point function (inverse of ``cdf`` --- percentiles).
isf(q, df, loc=0, scale=1)
    Inverse survival function (inverse of ``sf``).
moment(order, df, loc=0, scale=1)
    Non-central moment of the specified order.
stats(df, loc=0, scale=1, moments='mv')
    Mean('m'), variance('v'), skew('s'), and/or kurtosis('k').
entropy(df, loc=0, scale=1)
    (Differential) entropy of the RV.
fit(data)
    Parameter estimates for generic data.
    See `scipy.stats.rv_continuous.fit <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rv_continuous.fit.html#scipy.stats.rv_continuous.fit>`__ for detailed documentation of the
    keyword arguments.
expect(func, args=(df,), loc=0, scale=1, lb=None, ub=None, conditional=False, **kwds)
    Expected value of a function (of one argument) with respect to the distribution.
median(df, loc=0, scale=1)
    Median of the distribution.
mean(df, loc=0, scale=1)
    Mean of the distribution.
var(df, loc=0, scale=1)
    Variance of the distribution.
std(df, loc=0, scale=1)
    Standard deviation of the distribution.
interval(confidence, df, loc=0, scale=1)
    Confidence interval with equal areas around the median.

Notes
-----
The probability density function for `chi2` is:

.. math::
```
