NumPy 2.5.3 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Transform discrete distributions with FFT conventions

np.fft.fft and ifft use different exponential signs; ifft includes 1/N. Keep grid spacing, offset phase and normalization consistent. Inverting a characteristic function is not automatically the same sign convention as transforming a PMF. Check mass, imaginary residue and wraparound; increase support/zero padding to assess aliasing, not arbitrary clipping.

```python
import numpy as np
p=np.array([.2,.5,.3,0.]); z=np.fft.ifft(np.fft.fft(p))
assert np.allclose(z.real,p) and abs(z.imag).max()<1e-12
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
