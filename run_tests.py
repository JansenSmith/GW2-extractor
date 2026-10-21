"""Run the whole test suite. No API key, no network, nothing written outside a tempdir.

    python run_tests.py

Equivalent to `python -m unittest discover -s tests -t .` from the repo root.
"""

import os
import sys
import unittest

if __name__ == '__main__':
    # Anchored on this file, not the cwd, so it runs from anywhere.
    repo = os.path.dirname(os.path.abspath(__file__))
    suite = unittest.TestLoader().discover(start_dir=os.path.join(repo, 'tests'),
                                           top_level_dir=repo)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
