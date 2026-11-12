"""Fixed random numbers per patient.

Every random decision of a patient has a name (purpose) and a week. The same
seed, patient, purpose and week always give the same number. A scenario
changes probabilities, not the random numbers, so the same patient can be
simulated under several scenarios and differs only where an intervention
acts (common random numbers).
"""
from statistics import NormalDist

_MASK = (1 << 64) - 1
_NORMAL = NormalDist()
_PURPOSES = {}


def _mix(x):
    x &= _MASK
    x ^= x >> 30
    x = (x * 0xBF58476D1CE4E5B9) & _MASK
    x ^= x >> 27
    x = (x * 0x94D049BB133111EB) & _MASK
    return x ^ (x >> 31)


def purpose(name):
    """Number of a purpose. Names are registered on first use."""
    if name not in _PURPOSES:
        _PURPOSES[name] = int.from_bytes(name.encode(), "big") % 1000003
    return _PURPOSES[name]


class Draws:
    def __init__(self, seed, index):
        self.base = _mix(seed * 0x9E3779B97F4A7C15 + index + 1)

    def key(self, name, week=0):
        """A whole number for a purpose and week, e.g. as seed of a generator."""
        return _mix(self.base ^ _mix(purpose(name) * 0x9E3779B97F4A7C15 + week + 1))

    def u(self, name, week=0):
        """Uniform number in [0, 1)."""
        return (self.key(name, week) >> 11) / 9007199254740992.0

    def normal(self, name, week=0):
        """Standard normal number."""
        return _NORMAL.inv_cdf(min(max(self.u(name, week), 1e-12), 1 - 1e-12))

    def pick(self, name, probabilities, week=0):
        """Key of a {key: probability} mapping; the key 'basis' is skipped."""
        keys = [k for k in probabilities if k != "basis"]
        total = sum(probabilities[k] for k in keys)
        x = self.u(name, week) * total
        for k in keys:
            x -= probabilities[k]
            if x < 0:
                return k
        return keys[-1]
