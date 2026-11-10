# Official API description: arch.univariate.base.ARCHModelResult.conditional_volatility (arch 8.0.0)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
arch.univariate.base.ARCHModelResult.conditional_volatility

Estimated conditional volatility

Returns
-------
conditional_volatility : {ndarray, Series}
    nobs element array containing the conditional volatility (square
    root of conditional variance).  The values are aligned with the
    input data so that the value in the t-th position is the variance
    of t-th error, which is computed using time-(t-1) information.
```
