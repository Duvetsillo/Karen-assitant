"""Read the foreground Windows window only after an explicit user command."""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import unicodedata


def _clean(value, limit=200):
    return ' '.join(''.join(char if not unicodedata.category(char).startswith('C') else ' '
                            for char in value).split())[:limit]


def active_window():
    if os.name != 'nt':
        raise OSError('La consulta de ventana activa requiere Windows.')
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        raise OSError('No hay una ventana activa disponible.')
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    length = min(max(user32.GetWindowTextLengthW(hwnd), 0), 500)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    result = {'title': _clean(buffer.value) or '(sin título)'}
    if pid.value:
        result['pid'] = pid.value
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                        wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x1000, False, pid.value)
        if handle:
            try:
                path = ctypes.create_unicode_buffer(32768)
                size = wintypes.DWORD(len(path))
                if kernel32.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
                    result['process'] = _clean(Path(path.value).name, 100)
            finally:
                kernel32.CloseHandle(handle)
    return result
