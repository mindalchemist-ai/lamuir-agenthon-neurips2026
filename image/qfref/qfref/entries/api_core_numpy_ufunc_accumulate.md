# Official API description: numpy.ufunc.accumulate (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary and parameters are omitted.

```text
numpy.ufunc.accumulate(self, array, /, axis=0, dtype=None, out=None)

accumulate(array, axis=0, dtype=None, out=None)

Accumulate the result of applying the operator to all elements.

For a one-dimensional array, accumulate produces results equivalent to::

  r = np.empty(len(A))
  t = op.identity        # op = the ufunc being applied to A's  elements
  for i in range(len(A)):
      t = op(t, A[i])
      r[i] = t
  return r

For example, add.accumulate() is equivalent to np.cumsum().

For a multi-dimensional array, accumulate is applied along only one
axis (axis zero by default; see Examples below) so repeated use is
necessary if one wants to accumulate over multiple axes.

Parameters
----------
array : array_like
    The array to act on.
axis : int, optional
    The axis along which to apply the accumulation; default is zero.
dtype : data-type code, optional
    The data-type used to represent the intermediate results. Defaults
    to the data-type of the output array if such is provided, or the
    data-type of the input array if no output array is provided.
out : ndarray, None, or tuple of ndarray and None, optional
    Location into which the result is stored.
    If not provided or None, a freshly-allocated array is returned.
    For consistency with ``ufunc.__call__``, if passed as a keyword
    argument, can be Ellipses (``out=...``, which has the same effect
    as None as an array is always returned), or a 1-element tuple.

Returns
-------
r : ndarray
    The accumulated values. If `out` was supplied, `r` is a reference to
    `out`.
```
