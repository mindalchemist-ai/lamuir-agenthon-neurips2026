# Official API description: numpy.cov (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
numpy.cov(m, y=None, rowvar=True, bias=False, ddof=None, fweights=None, aweights=None, *, dtype=None)

Estimate a covariance matrix, given data and weights.

Covariance indicates the level to which two variables vary together.
If we examine N-dimensional samples, :math:`X = [x_1, x_2, ..., x_N]^T`,
then the covariance matrix element :math:`C_{ij}` is the covariance of
:math:`x_i` and :math:`x_j`. The element :math:`C_{ii}` is the variance
of :math:`x_i`.

See the notes for an outline of the algorithm.

Parameters
----------
m : array_like
    A 1-D or 2-D array containing multiple variables and observations.
    Each row of `m` represents a variable, and each column a single
    observation of all those variables. Also see `rowvar` below.
y : array_like, optional
    An additional set of variables and observations. `y` has the same form
    as that of `m`.
rowvar : bool, optional
    If `rowvar` is True (default), then each row represents a
    variable, with observations in the columns. Otherwise, the relationship
    is transposed: each column represents a variable, while the rows
    contain observations.
bias : bool, optional
    Default normalization (False) is by ``(N - 1)``, where ``N`` is the
    number of observations given (unbiased estimate). If `bias` is True,
    then normalization is by ``N``. These values can be overridden by using
    the keyword ``ddof`` in numpy versions >= 1.5.
ddof : int, optional
    If not ``None`` the default value implied by `bias` is overridden.
    Note that ``ddof=1`` will return the unbiased estimate, even if both
    `fweights` and `aweights` are specified, and ``ddof=0`` will return
    the simple average. See the notes for the details. The default value
    is ``None``.
fweights : array_like, int, optional
    1-D array of integer frequency weights; the number of times each
    observation vector should be repeated.
aweights : array_like, optional
    1-D array of observation vector weights. These relative weights are
    typically large for observations considered "important" and smaller for
    observations considered less "important". If ``ddof=0`` the array of
    weights can be used to assign probabilities to observation vectors.
dtype : data-type, optional
    Data-type of the result. By default, the return data-type will have
    at least `numpy.float64` precision.

    .. versionadded:: 1.20

Returns
-------
out : ndarray
    The covariance matrix of the variables.

Notes
-----
Assume that the observations are in the columns of the observation
array `m` and let ``f = fweights`` and ``a = aweights`` for brevity. The
steps to compute the weighted covariance are as follows::

    >>> m = np.arange(10, dtype=np.float64)
    >>> f = np.arange(10) * 2
    >>> a = np.arange(10) ** 2.
    >>> ddof = 1
    >>> w = f * a
    >>> v1 = np.sum(w)
    >>> v2 = np.sum(w * a)
    >>> m -= np.sum(m * w, axis=None, keepdims=True) / v1
    >>> cov = np.dot(m * w, m.T) * v1 / (v1**2 - ddof * v2)

Note that when ``a == 1``, the normalization factor
``v1 / (v1**2 - ddof * v2)`` goes over to ``1 / (np.sum(f) - ddof)``
as it should.
```
