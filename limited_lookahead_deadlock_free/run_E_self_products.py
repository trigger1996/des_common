"""Run the E seven-/eight-copy products from PyCharm or the command line."""

import os
from pathlib import Path
import sys

from early_stop_products import main


if __name__ == '__main__':
    os.chdir(Path(__file__).resolve().parent)
    sys.argv[1:1] = ['--case', 'E', '--copies', '7', '8']
    main()
