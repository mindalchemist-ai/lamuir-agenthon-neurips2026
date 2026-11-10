# Official API description: numpy.quantile (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
numpy.quantile(a, q, axis=None, out=None, overwrite_input=False, method='linear', keepdims=False, *, weights=None)

Compute the q-th quantile of the data along the specified axis.

Parameters
----------
a : array_like of real numbers
    Input array or object that can be converted to an array.
q : array_like of float
    Probability or sequence of probabilities of the quantiles to compute.
    Values must be between 0 and 1 inclusive.
axis : {int, tuple of int, None}, optional
    Axis or axes along which the quantiles are computed. The default is
    to compute the quantile(s) along a flattened version of the array.
out : ndarray, optional
    Alternative output array in which to place the result. It must have
    the same shape and buffer length as the expected output, but the
    type (of the output) will be cast if necessary.
overwrite_input : bool, optional
    If True, then allow the input array `a` to be modified by
    intermediate calculations, to save memory. In this case, the
    contents of the input `a` after this function completes is
    undefined.
method : str, optional
    This parameter specifies the method to use for estimating the
    quantile.  There are many different methods, some unique to NumPy.
    The recommended options, numbered as they appear in [1]_, are:

    1. 'inverted_cdf'
    2. 'averaged_inverted_cdf'
    3. 'closest_observation'
    4. 'interpolated_inverted_cdf'
    5. 'hazen'
    6. 'weibull'
    7. 'linear'  (default)
    8. 'median_unbiased'
    9. 'normal_unbiased'

    The first three methods are discontinuous. For backward compatibility
    with previous versions of NumPy, the following discontinuous variations
    of the default 'linear' (7.) option are available:

    * 'lower'
    * 'higher',
    * 'midpoint'
    * 'nearest'

    See Notes for details.

    .. versionchanged:: 1.22.0
        This argument was previously called "interpolation" and only
        offered the "linear" default and last four options.

keepdims : bool, optional
    If this is set to True, the axes which are reduced are left in
    the result as dimensions with size one. With this option, the
    result will broadcast correctly against the original array `a`.

weights : array_like, optional
    An array of weights associated with the values in `a`. Each value in
    `a` contributes to the quantile according to its associated weight.
    The weights array can either be 1-D (in which case its length must be
    the size of `a` along the given axis) or of the same shape as `a`.
    If `weights=None`, then all data in `a` are assumed to have a
    weight equal to one.
    Only `method="inverted_cdf"` supports weights.
    See the notes for more details.

    .. versionadded:: 2.0.0

Returns
-------
quantile : scalar or ndarray
    If `q` is a single probability and `axis=None`, then the result
    is a scalar. If multiple probability levels are given, first axis
    of the result corresponds to the quantiles. The other axes are
    the axes that remain after the reduction of `a`. If the input
    contains integers or floats smaller than ``float64``, the output
    data-type is ``float64``. Otherwise, the output data-type is the
    same as that of the input. If `out` is specified, that array is
    returned instead.
```
