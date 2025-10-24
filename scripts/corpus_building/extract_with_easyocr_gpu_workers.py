#!/usr/bin/env python3
"""
EasyOCR extraction - Optimized for NVIDIA GPU with high worker count
Variant A: 8 CPU workers for parallel preprocessing
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / "../.."))

# Import original script
from scripts.corpus_building.extract_with_easyocr import *  # noqa: F403, F405

# Override worker count for GPU optimization
WORKERS = 8  # High worker count for parallel CPU preprocessing

if __name__ == "__main__":
    # Patch the readtext call to use 8 workers
    import easyocr

    original_readtext = easyocr.Reader.readtext

    def readtext_with_workers(self, *args, **kwargs):
        kwargs["workers"] = WORKERS
        return original_readtext(self, *args, **kwargs)

    easyocr.Reader.readtext = readtext_with_workers

    # Run main extraction
    main()  # noqa: F405
