"""Fixed random numbers per patient.

Every random decision of a patient has a name (purpose) and a week. The same
seed, patient, purpose and week always give the same number. A scenario
changes probabilities, not the random numbers, so the same patient can be
simulated under several scenarios and differs only where an intervention
acts (common random numbers).
"""
import hashlib
from statistics import NormalDist

_MASK = (1 << 64) - 1
_NORMAL = NormalDist()
_PURPOSES = {}


def _mix(x):
    """SplitMix64 finaliser: turns a 64-bit number into a well-mixed one, so that
    nearby inputs give unrelated outputs."""
    x &= _MASK
    x ^= x >> 30
    x = (x * 0xBF58476D1CE4E5B9) & _MASK
    x ^= x >> 27
    x = (x * 0x94D049BB133111EB) & _MASK
    return x ^ (x >> 31)


def purpose(name):
    """Number of a purpose: the first 64 bits of the SHA-256 hash of its name.
    Different names practically never get the same number (the chance for 1000
    names is about 3 in 10^14), so the random numbers of two purposes are not
    coupled. Names are hashed once and kept."""
    if name not in _PURPOSES:
        _PURPOSES[name] = int.from_bytes(hashlib.sha256(name.encode()).digest()[:8], "big")
    return _PURPOSES[name]


class Draws:
    """The fixed random numbers of one patient: the same seed, patient, purpose and
    week give the same number."""
    def __init__(self, seed, index):
        """Base value of the patient from the seed and the patient's index in the
        cohort."""
        # 0x9E37... is 2^64 divided by the golden ratio: it spreads consecutive
        # seeds and indices far apart before mixing.
        self.base = _mix(seed * 0x9E3779B97F4A7C15 + index + 1)

    def key(self, name, week=0):
        """A whole number for a purpose and week, e.g. as seed of a generator."""
        return _mix(self.base ^ _mix(purpose(name) * 0x9E3779B97F4A7C15 + week + 1))

    def u(self, name, week=0):
        """Uniform number in [0, 1)."""
        # The top 53 bits divided by 2^53: every double in [0, 1) with full precision.
        return (self.key(name, week) >> 11) / 9007199254740992.0

    def normal(self, name, week=0):
        """Standard normal number."""
        # Inverse of the normal distribution; u is kept away from 0, where it is infinite.
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
