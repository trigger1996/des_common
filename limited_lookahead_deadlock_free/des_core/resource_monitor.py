"""OS process measurements for reproducible DES experiments.

CPU usage is reported both per logical core and normalized over the machine.
Working set (resident RAM), private committed bytes and Python allocation
peaks are distinct quantities and must not be substituted for one another.
"""

import ctypes
from ctypes import wintypes
import os
import platform
import sys
from time import perf_counter


class _ProcessMemory(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
        (name, ctypes.c_size_t) for name in ('peak_working', 'working', 'peak_paged', 'paged',
            'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile', 'private')]


def process_snapshot(handle=-1):
    if sys.platform != 'win32':
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)

        return dict(wall=perf_counter(), cpu_user_seconds=usage.ru_utime,
                    cpu_kernel_seconds=usage.ru_stime,
                    peak_working_set_bytes=int(usage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024)))

    memory = _ProcessMemory()
    memory.cb = ctypes.sizeof(memory)
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ProcessMemory), wintypes.DWORD]
    query.restype = wintypes.BOOL
    process = wintypes.HANDLE(int(handle))

    if not query(process, ctypes.byref(memory), memory.cb):
        raise ctypes.WinError()

    times = [wintypes.FILETIME() for _ in range(4)]

    if not ctypes.windll.kernel32.GetProcessTimes(process, *(ctypes.byref(t) for t in times)):
        raise ctypes.WinError()

    seconds = lambda value: ((value.dwHighDateTime << 32) | value.dwLowDateTime) / 10_000_000

    return dict(wall=perf_counter(), cpu_user_seconds=seconds(times[3]),
                cpu_kernel_seconds=seconds(times[2]), working_set_bytes=memory.working,
                peak_working_set_bytes=memory.peak_working, private_bytes=memory.private,
                peak_commit_bytes=memory.peak_pagefile, page_faults=memory.faults)


def interval_usage(before, after):
    wall = max(0., after['wall'] - before['wall'])
    user = max(0., after['cpu_user_seconds'] - before['cpu_user_seconds'])
    kernel = max(0., after['cpu_kernel_seconds'] - before['cpu_kernel_seconds'])
    core_percent = 100 * (user + kernel) / wall if wall else 0.

    return dict(wall_seconds=wall, cpu_user_seconds=user, cpu_kernel_seconds=kernel,
                cpu_seconds=user + kernel, cpu_percent_one_core=core_percent,
                cpu_percent_machine=core_percent / (os.cpu_count() or 1),
                working_set_bytes=after.get('working_set_bytes'),
                peak_working_set_bytes=after['peak_working_set_bytes'],
                private_bytes=after.get('private_bytes'), peak_commit_bytes=after.get('peak_commit_bytes'),
                cpu_resolution_note='Windows process CPU counters may round a sub-millisecond solve to zero; '
                                    'use batch aggregates rather than interpreting zero as no CPU work.')


def environment_record():
    from importlib.metadata import version, PackageNotFoundError

    cpu_name = platform.processor()

    if sys.platform == 'win32':
        import winreg
        from examples.large_scale.large_scale_overall import memory_status

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            cpu_name = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()

        memory = memory_status()
    else:
        memory = dict(total_bytes=os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES'))

    packages = {}

    for name in ('numpy', 'networkx', 'matplotlib', 'pillow', 'pymupdf'):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = 'not installed'

    return dict(python=sys.version, implementation=platform.python_implementation(), packages=packages,
                os=platform.platform(), cpu=cpu_name, logical_processors=os.cpu_count(),
                ram=memory, architecture=platform.machine(),
                state_representation='Explicit dictionary keys (q_hat, frozenset(x_hat)) for both methods; '
                                     'observation states (frozenset(x), frozenset(gamma_c)); '
                                     'shared immutable UR/NX fragments preserve observation consistency.',
                memory_scope='OS peak working set and committed/private memory; Python tracemalloc '
                             'allocation peak is recorded separately for small-model experiments.')
