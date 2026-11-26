"""Run the requested P7/P8 LL entry point, including its RAM feasibility check."""

import os
from pathlib import Path
import sys

from large_scale_overall import main


if __name__ == '__main__':
    os.chdir(Path(__file__).resolve().parent)
    sys.argv[1:1] = ['--run', '--cases', 'products', '--copies', '7', '8',
                     '--methods', 'll', '--max-memory-gib', '10']
    main()
