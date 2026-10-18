"""Retained Windows process handles; failures are never interpreted as exit.

The controller establishes ownership before allowing termination. Only the owned
ancestry is returned; the transient system process inventory is not recorded.
"""
import ctypes
from ctypes import wintypes as w
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import time

WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
WAIT_FAILED = 0xFFFFFFFF


class ProcessEntry(ctypes.Structure):
    _fields_ = [('dwSize', w.DWORD), ('cntUsage', w.DWORD), ('th32ProcessID', w.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', w.DWORD),
                ('cntThreads', w.DWORD), ('th32ParentProcessID', w.DWORD),
                ('pcPriClassBase', w.LONG), ('dwFlags', w.DWORD), ('szExeFile', w.WCHAR * 260)]


@lru_cache(maxsize=1)
def api():
    if os.name != 'nt':
        raise RuntimeError('Live process observation requires Windows')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        'CloseHandle': ([w.HANDLE], w.BOOL),
        'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
        'GetExitCodeProcess': ([w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
        'GetProcessTimes': ([w.HANDLE] + [ctypes.POINTER(w.FILETIME)] * 4, w.BOOL),
        'QueryFullProcessImageNameW': ([w.HANDLE, w.DWORD, w.LPWSTR, ctypes.POINTER(w.DWORD)], w.BOOL),
        'TerminateProcess': ([w.HANDLE, w.UINT], w.BOOL),
        'GetCurrentProcess': ([], w.HANDLE),
        'DuplicateHandle': ([w.HANDLE, w.HANDLE, w.HANDLE, ctypes.POINTER(w.HANDLE),
                             w.DWORD, w.BOOL, w.DWORD], w.BOOL),
        'CreateToolhelp32Snapshot': ([w.DWORD, w.DWORD], w.HANDLE),
        'Process32FirstW': ([w.HANDLE, ctypes.POINTER(ProcessEntry)], w.BOOL),
        'Process32NextW': ([w.HANDLE, ctypes.POINTER(ProcessEntry)], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        function = getattr(kernel, name)
        function.argtypes = args
        function.restype = result
    return kernel


def checked(value):
    if not value:
        raise ctypes.WinError(ctypes.get_last_error())
    return value


def filetime(value):
    return (value.dwHighDateTime << 32) | value.dwLowDateTime


def process_table():
    kernel = api()
    handle = kernel.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        more = kernel.Process32FirstW(handle, ctypes.byref(entry))
        result = {}
        while more:
            result[entry.th32ProcessID] = {'parent': entry.th32ParentProcessID,
                                           'image_name': entry.szExeFile}
            more = kernel.Process32NextW(handle, ctypes.byref(entry))
        if ctypes.get_last_error() != 18:  # ERROR_NO_MORE_FILES
            raise ctypes.WinError(ctypes.get_last_error())
        return result
    finally:
        checked(kernel.CloseHandle(handle))


class Process:
    def __init__(self, pid, expected_image, *, handle=None, owned=False):
        self.kernel = api()
        self.pid = int(pid)
        self.owned = owned
        self.handle = handle or checked(self.kernel.OpenProcess(0x100000 | 0x1000 | 0x1, False, self.pid))
        try:
            size = w.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            checked(self.kernel.QueryFullProcessImageNameW(self.handle, 0, buffer, ctypes.byref(size)))
            self.image = str(Path(buffer.value).resolve())
            if os.path.normcase(self.image) != os.path.normcase(str(Path(expected_image).resolve())):
                raise RuntimeError('Process executable did not match the expected owned executable')
            self.digest = hashlib.sha256(Path(self.image).read_bytes()).hexdigest()
            self.creation = self._times()[0]
        except BaseException:
            self.close()
            raise

    @classmethod
    def from_popen(cls, child, expected_image):
        # CPython's Windows Popen retains the original process handle. Duplicate
        # that handle, rather than reopening an exited/reused numeric PID.
        if os.name != 'nt' or not hasattr(child, '_handle'):
            raise RuntimeError('Expected a Windows CPython Popen process handle')
        kernel = api()
        duplicate = w.HANDLE()
        current = kernel.GetCurrentProcess()
        checked(kernel.DuplicateHandle(current, int(child._handle), current,
                                       ctypes.byref(duplicate), 0, False, 2))
        return cls(child.pid, expected_image, handle=duplicate.value, owned=True)

    def _times(self):
        values = [w.FILETIME() for _ in range(4)]
        checked(self.kernel.GetProcessTimes(self.handle, *[ctypes.byref(value) for value in values]))
        return tuple(filetime(value) for value in values)

    def observe(self, wait_ms=0):
        if not self.handle or not 0 <= wait_ms <= 30000:
            raise ValueError('Open handle and a finite bounded wait required')
        start = time.perf_counter_ns()
        result = self.kernel.WaitForSingleObject(self.handle, wait_ms)
        if result == WAIT_FAILED:
            raise ctypes.WinError(ctypes.get_last_error())
        if result not in (WAIT_OBJECT_0, WAIT_TIMEOUT):
            raise RuntimeError('Unexpected process wait result')
        creation, exit_time, _, _ = self._times()
        if creation != self.creation:
            raise RuntimeError('Retained process creation identity changed')
        exit_code = w.DWORD()
        checked(self.kernel.GetExitCodeProcess(self.handle, ctypes.byref(exit_code)))
        exited = result == WAIT_OBJECT_0
        return {'pid': self.pid, 'creation_time_100ns': creation,
                'image': self.image, 'image_sha256': self.digest,
                'start_ns': start, 'end_ns': time.perf_counter_ns(),
                'wait_result': result, 'alive': not exited,
                'exit_code': exit_code.value if exited else None,
                'exit_time_100ns': exit_time if exited else None}

    def terminate(self, exit_code=87):
        if not self.owned:
            raise RuntimeError('Refusing termination without established ownership')
        before = self.observe()
        if not before['alive']:
            return {'requested': False, 'before': before, 'after': before}
        start = time.perf_counter_ns()
        checked(self.kernel.TerminateProcess(self.handle, exit_code))
        returned = time.perf_counter_ns()
        after = self.observe(10000)
        if after['alive']:
            raise RuntimeError('Owned process termination did not settle within the deadline')
        return {'requested': True, 'request_start_ns': start, 'request_return_ns': returned,
                'before': before, 'after': after}

    def close(self):
        if self.handle:
            handle, self.handle = self.handle, None
            checked(self.kernel.CloseHandle(handle))


def bind_generator(pid, server, node_image, shell_image):
    """Require the observed Node -> configured shell -> owned server chain."""
    table = process_table()
    node_entry = table.get(pid)
    if not node_entry:
        raise RuntimeError('Generator was absent from the process snapshot')
    shell_pid = node_entry['parent']
    if table.get(shell_pid, {}).get('parent') != server.pid:
        raise RuntimeError('Generator ancestry did not reach the owned server through its shell')
    shell = Process(shell_pid, shell_image)
    try:
        generator = Process(pid, node_image)
        try:
            observations = {'server': server.observe(), 'shell': shell.observe(), 'generator': generator.observe()}
            if not all(item['alive'] for item in observations.values()):
                raise RuntimeError('Expected owned process chain was not alive')
            if not server.creation <= shell.creation <= generator.creation:
                raise RuntimeError('Process creation chronology contradicts ancestry')
            shell.owned = generator.owned = True
            return shell, generator, {'chain': [pid, shell_pid, server.pid], 'observations': observations}
        except BaseException:
            generator.close()
            raise
    except BaseException:
        shell.close()
        raise
