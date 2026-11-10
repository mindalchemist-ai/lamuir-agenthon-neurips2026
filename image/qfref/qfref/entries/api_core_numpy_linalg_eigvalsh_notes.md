# Official API description: numpy.linalg.eigvalsh (numpy 2.5.3)

From the installed docstring, unchanged; sections other than the signature, summary, parameters and notes are omitted.

```text
numpy.linalg.eigvalsh(a, UPLO='L')

Compute the eigenvalues of a complex Hermitian or real symmetric matrix.

Main difference from eigh: the eigenvectors are not computed.

Parameters
----------
a : (..., M, M) array_like
    A complex- or real-valued matrix whose eigenvalues are to be
    computed.
UPLO : {'L', 'U'}, optional
    Specifies whether the calculation is done with the lower triangular
    part of `a` ('L', default) or the upper triangular part ('U').
    Irrespective of this value only the real parts of the diagonal will
    be considered in the computation to preserve the notion of a Hermitian
    matrix. It therefore follows that the imaginary part of the diagonal
    will always be treated as zero.

Returns
-------
w : (..., M,) ndarray
    The eigenvalues in ascending order, each repeated according to
    its multiplicity.

Notes
-----
Broadcasting rules apply, see the `numpy.linalg` documentation for
details.

The eigenvalues are computed using LAPACK routines ``_syevd``, ``_heevd``.
```
