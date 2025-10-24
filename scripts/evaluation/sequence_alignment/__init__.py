"""
Sequence alignment algorithms for classification correction.

This package contains three approaches to global sequence alignment:
1. DP: Dynamic programming two-sequence alignment (globally optimal)
2. Two-Pass: Sequential Needleman-Wunsch alignment (simpler, not globally optimal)
3. HMM: Hidden Markov Model with Viterbi decoding (probabilistic)
"""

from .dp_alignment import dp_two_sequence_alignment
from .hmm_alignment import hmm_viterbi_alignment
from .two_pass_alignment import two_pass_alignment

__all__ = [
    "dp_two_sequence_alignment",
    "two_pass_alignment",
    "hmm_viterbi_alignment",
]
