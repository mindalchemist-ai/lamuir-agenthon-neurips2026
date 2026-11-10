# Official API description: numpy.ufunc.reduce (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
numpy.ufunc.reduce(self, array, /, axis=0, dtype=None, out=None, **kwargs)

reduce(array, axis=0, dtype=None, out=None, keepdims=False, initial=<no value>, where=True)

Reduces `array`'s dimension by one, by applying ufunc along one axis.

Let :math:`array.shape = (N_0, ..., N_i, ..., N_{M-1})`.  Then
:math:`ufunc.reduce(array, axis=i)[k_0, ..,k_{i-1}, k_{i+1}, .., k_{M-1}]` =
the result of iterating `j` over :math:`range(N_i)`, cumulatively applying
ufunc to each :math:`array[k_0, ..,k_{i-1}, j, k_{i+1}, .., k_{M-1}]`.
For a one-dimensional array, reduce produces results equivalent to:
::

 r = op.identity # op = ufunc
 for i in range(len(A)):
   r = op(r, A[i])
 return r

For example, add.reduce() is equivalent to sum().

Parameters
----------
array : array_like
    The array to act on.
axis : None or int or tuple of ints, optional
    Axis or axes along which a reduction is performed.
    The default (`axis` = 0) is perform a reduction over the first
    dimension of the input array. `axis` may be negative, in
    which case it counts from the last to the first axis.

    If this is None, a reduction is performed over all the axes.
    If this is a tuple of ints, a reduction is performed on multiple
    axes, instead of a single axis or all the axes as before.

    For operations which are either not commutative or not associative,
    doing a reduction over multiple axes is not well-defined. The
    ufuncs do not currently raise an exception in this case, but will
    likely do so in the future.
dtype : data-type code, optional
    The data type used to perform the operation. Defaults to that of
    ``out`` if given, and the data type of ``array`` otherwise (though
    upcast to conserve precision for some cases, such as
    ``numpy.add.reduce`` for integer or boolean input).
out : ndarray, None, ..., or tuple of ndarray and None, optional
    Location into which the result is stored.
    If not provided or None, a freshly-allocated array is returned.
    If passed as a keyword argument, can be Ellipses (``out=...``) to
    ensure an array is returned even if the result is 0-dimensional
    (which is useful especially for object dtype), or a 1-element tuple
    (latter for consistency with ``ufunc.__call__``).

    .. versionadded:: 2.3
        Support for ``out=...`` was added.

keepdims : bool, optional
    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the original `array`.
initial : scalar, optional
    The value with which to start the reduction.
    If the ufunc has no identity or the dtype is object, this defaults
    to None - otherwise it defaults to ufunc.identity.
    If ``None`` is given, the first element of the reduction is used,
    and an error is thrown if the reduction is empty.
where : array_like of bool, optional
    A boolean array which is broadcasted to match the dimensions
    of `array`, and selects elements to include in the reduction. Note
    that for ufuncs like ``minimum`` that do not have an identity
    defined, one has to pass in also ``initial``.

Returns
-------
r : ndarray
    The reduced array. If `out` was supplied, `r` is a reference to it.
```
