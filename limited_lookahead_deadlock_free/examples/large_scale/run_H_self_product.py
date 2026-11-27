"""Run the H four-copy product from PyCharm or the command line."""

# Allow direct execution from the project working directory.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))


import os
from pathlib import Path
import sys

from examples.large_scale.early_stop_products import main


if __name__ == '__main__':
    os.chdir(Path(__file__).resolve().parents[2])
    sys.argv[1:1] = ['--case', 'H', '--copies', '4']
    main()
