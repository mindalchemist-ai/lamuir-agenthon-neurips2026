# Official API description: numpy.corrcoef (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
numpy.corrcoef(x, y=None, rowvar=True, *, dtype=None)

Return Pearson product-moment correlation coefficients.

Please refer to the documentation for `cov` for more detail.  The
relationship between the correlation coefficient matrix, `R`, and the
covariance matrix, `C`, is

.. math:: R_{ij} = \frac{ C_{ij} } { \sqrt{ C_{ii} C_{jj} } }

The values of `R` are between -1 and 1, inclusive.

Parameters
----------
x : array_like
    A 1-D or 2-D array containing multiple variables and observations.
    Each row of `x` represents a variable, and each column a single
    observation of all those variables. Also see `rowvar` below.
y : array_like, optional
    An additional set of variables and observations. `y` has the same
    shape as `x`.
rowvar : bool, optional
    If `rowvar` is True (default), then each row represents a
    variable, with observations in the columns. Otherwise, the relationship
    is transposed: each column represents a variable, while the rows
    contain observations.

dtype : data-type, optional
    Data-type of the result. By default, the return data-type will have
    at least `numpy.float64` precision.

    .. versionadded:: 1.20

Returns
-------
R : ndarray
    The correlation coefficient matrix of the variables.

Notes
-----
Due to floating point rounding the resulting array may not be Hermitian,
the diagonal elements may not be 1, and the elements may not satisfy the
inequality abs(a) <= 1. The real and imaginary parts are clipped to the
interval [-1,  1] in an attempt to improve on that situation but is not
much help in the complex case.
```
