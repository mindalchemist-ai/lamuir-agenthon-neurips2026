# Official API description: numpy.median (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
numpy.median(a, axis=None, out=None, overwrite_input=False, keepdims=False)

Compute the median along the specified axis.

Returns the median of the array elements.

Parameters
----------
a : array_like
    Input array or object that can be converted to an array.
axis : {int, sequence of int, None}, optional
    Axis or axes along which the medians are computed. The default,
    axis=None, will compute the median along a flattened version of
    the array. If a sequence of axes, the array is first flattened
    along the given axes, then the median is computed along the
    resulting flattened axis.
out : ndarray, optional
    Alternative output array in which to place the result. It must
    have the same shape and buffer length as the expected output,
    but the type (of the output) will be cast if necessary.
overwrite_input : bool, optional
   If True, then allow use of memory of input array `a` for
   calculations. The input array will be modified by the call to
   `median`. This will save memory when you do not need to preserve
   the contents of the input array. Treat the input as undefined,
   but it will probably be fully or partially sorted. Default is
   False. If `overwrite_input` is ``True`` and `a` is not already an
   `ndarray`, an error will be raised.
keepdims : bool, optional
    If this is set to True, the axes which are reduced are left
    in the result as dimensions with size one. With this option,
    the result will broadcast correctly against the original `arr`.

Returns
-------
median : ndarray
    A new array holding the result. If the input contains integers
    or floats smaller than ``float64``, then the output data-type is
    ``np.float64``.  Otherwise, the data-type of the output is the
    same as that of the input. If `out` is specified, that array is
    returned instead.

Notes
-----
Given a vector ``V`` of length ``N``, the median of ``V`` is the
middle value of a sorted copy of ``V``, ``V_sorted`` - i
e., ``V_sorted[(N-1)/2]``, when ``N`` is odd, and the average of the
two middle values of ``V_sorted`` when ``N`` is even.
```
