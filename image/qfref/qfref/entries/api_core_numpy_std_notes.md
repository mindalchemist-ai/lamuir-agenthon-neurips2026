# Official API description: numpy.std (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
numpy.std(a, axis=None, dtype=None, out=None, ddof=0, keepdims=<no value>, *, where=<no value>, mean=<no value>, correction=<no value>)

Compute the standard deviation along the specified axis.

Returns the standard deviation, a measure of the spread of a distribution,
of the array elements. The standard deviation is computed for the
flattened array by default, otherwise over the specified axis.

Parameters
----------
a : array_like
    Calculate the standard deviation of these values.
axis : None or int or tuple of ints, optional
    Axis or axes along which the standard deviation is computed. The
    default is to compute the standard deviation of the flattened array.
    If this is a tuple of ints, a standard deviation is performed over
    multiple axes, instead of a single axis or all the axes as before.
dtype : dtype, optional
    Type to use in computing the standard deviation. For arrays of
    integer type the default is float64, for arrays of float types it is
    the same as the array type.
out : ndarray, optional
    Alternative output array in which to place the result. It must have
    the same shape as the expected output but the type (of the calculated
    values) will be cast if necessary.
    See :ref:`ufuncs-output-type` for more details.
ddof : {int, float}, optional
    Means Delta Degrees of Freedom.  The divisor used in calculations
    is ``N - ddof``, where ``N`` represents the number of elements.
    By default `ddof` is zero. See Notes for details about use of `ddof`.
keepdims : bool, optional
    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the input array.

    If the default value is passed, then `keepdims` will not be
    passed through to the `std` method of sub-classes of
    `ndarray`, however any non-default value will be.  If the
    sub-class' method does not implement `keepdims` any
    exceptions will be raised.
where : array_like of bool, optional
    Elements to include in the standard deviation.
    See `~numpy.ufunc.reduce` for details.

    .. versionadded:: 1.20.0

mean : array_like, optional
    Provide the mean to prevent its recalculation. The mean should have
    a shape as if it was calculated with ``keepdims=True``.
    The axis for the calculation of the mean should be the same as used in
    the call to this std function.

    .. versionadded:: 2.0.0

correction : {int, float}, optional
    Array API compatible name for the ``ddof`` parameter. Only one of them
    can be provided at the same time.

    .. versionadded:: 2.0.0

Returns
-------
standard_deviation : ndarray, see dtype parameter above.
    If `out` is None, return a new array containing the standard deviation,
    otherwise return a reference to the output array.

Notes
-----
There are several common variants of the array standard deviation
calculation. Assuming the input `a` is a one-dimensional NumPy array
and ``mean`` is either provided as an argument or computed as
``a.mean()``, NumPy computes the standard deviation of an array as::

    N = len(a)
    d2 = abs(a - mean)**2  # abs is for complex `a`
    var = d2.sum() / (N - ddof)  # note use of `ddof`
    std = var**0.5

Different values of the argument `ddof` are useful in different
contexts. NumPy's default ``ddof=0`` corresponds with the expression:

.. math::

    \sqrt{\frac{\sum_i{|a_i - \bar{a}|^2 }}{N}}

which is sometimes called the "population standard deviation" in the field
of statistics because it applies the definition of standard deviation to
`a` as if `a` were a complete population of possible observations.

Many other libraries define the standard deviation of an array
differently, e.g.:

.. math::

    \sqrt{\frac{\sum_i{|a_i - \bar{a}|^2 }}{N - 1}}

In statistics, the resulting quantity is sometimes called the "sample
standard deviation" because if `a` is a random sample from a larger
population, this calculation provides the square root of an unbiased
estimate of the variance of the population. The use of :math:`N-1` in the
denominator is often called "Bessel's correction" because it corrects for
bias (toward lower values) in the variance estimate introduced when the
sample mean of `a` is used in place of the true mean of the population.
The resulting estimate of the standard deviation is still biased, but less
than it would have been without the correction. For this quantity, use
``ddof=1``.

Note that, for complex numbers, `std` takes the absolute
value before squaring, so that the result is always real and nonnegative.

For floating-point input, the standard deviation is computed using the same
precision the input has. Depending on the input data, this can cause
the results to be inaccurate, especially for float32 (see example below).
Specifying a higher-accuracy accumulator using the `dtype` keyword can
alleviate this issue.
```
