# Official API description: numpy.quantile (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

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

Notes
-----
Given a sample `a` from an underlying distribution, `quantile` provides a
nonparametric estimate of the inverse cumulative distribution function.

By default, this is done by interpolating between adjacent elements in
``y``, a sorted copy of `a`::

    (1-g)*y[j] + g*y[j+1]

where the index ``j`` and coefficient ``g`` are the integral and
fractional components of ``q * (n-1)``, and ``n`` is the number of
elements in the sample.

This is a special case of Equation 1 of H&F [1]_. More generally,

- ``j = (q*n + m - 1) // 1``, and
- ``g = (q*n + m - 1) % 1``,

where ``m`` may be defined according to several different conventions.
The preferred convention may be selected using the ``method`` parameter:

=============================== =============== ===============
``method``                      number in H&F   ``m``
=============================== =============== ===============
``interpolated_inverted_cdf``   4               ``0``
``hazen``                       5               ``1/2``
``weibull``                     6               ``q``
``linear`` (default)            7               ``1 - q``
``median_unbiased``             8               ``q/3 + 1/3``
``normal_unbiased``             9               ``q/4 + 3/8``
=============================== =============== ===============

Note that indices ``j`` and ``j + 1`` are clipped to the range ``0`` to
``n - 1`` when the results of the formula would be outside the allowed
range of non-negative indices. The ``- 1`` in the formulas for ``j`` and
``g`` accounts for Python's 0-based indexing.

The table above includes only the estimators from H&F that are continuous
functions of probability `q` (estimators 4-9). NumPy also provides the
three discontinuous estimators from H&F (estimators 1-3), where ``j`` is
defined as above, ``m`` is defined as follows, and ``g`` is a function
of the real-valued ``index = q*n + m - 1`` and ``j``.

1. ``inverted_cdf``: ``m = 0`` and ``g = int(index - j > 0)``
2. ``averaged_inverted_cdf``: ``m = 0`` and
   ``g = (1 + int(index - j > 0)) / 2``
3. ``closest_observation``: ``m = -1/2`` and
   ``g = 1 - int((index == j) & (j%2 == 1))``

For backward compatibility with previous versions of NumPy, `quantile`
provides four additional discontinuous estimators. Like
``method='linear'``, all have ``m = 1 - q`` so that ``j = q*(n-1) // 1``,
but ``g`` is defined as follows.

- ``lower``: ``g = 0``
- ``midpoint``: ``g = 0.5``
- ``higher``: ``g = 1``
- ``nearest``: ``g = (q*(n-1) % 1) > 0.5``

**Weighted quantiles:**
More formally, the quantile at probability level :math:`q` of a cumulative
distribution function :math:`F(y)=P(Y \leq y)` with probability measure
:math:`P` is defined as any number :math:`x` that fulfills the
*coverage conditions*

.. math:: P(Y < x) \leq q \quad\text{and}\quad P(Y \leq x) \geq q

with random variable :math:`Y\sim P`.
Sample quantiles, the result of `quantile`, provide nonparametric
estimation of the underlying population counterparts, represented by the
unknown :math:`F`, given a data vector `a` of length ``n``.

Some of the estimators above arise when one considers :math:`F` as the
empirical distribution function of the data, i.e.
:math:`F(y) = \frac{1}{n} \sum_i 1_{a_i \leq y}`.
Then, different methods correspond to different choices of :math:`x` that
fulfill the above coverage conditions. Methods that follow this approach
are ``inverted_cdf`` and ``averaged_inverted_cdf``.

For weighted quantiles, the coverage conditions still hold. The
empirical cumulative distribution is simply replaced by its weighted
version, i.e.
:math:`P(Y \leq t) = \frac{1}{\sum_i w_i} \sum_i w_i 1_{x_i \leq t}`.
Only ``method="inverted_cdf"`` supports weights.
```
