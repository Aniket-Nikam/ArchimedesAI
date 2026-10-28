"""Windows DPAPI credential storage, bound to the current Windows account."""

import ctypes
import os
from ctypes import wintypes
from pathlib import Path

STORE = Path(__file__).resolve().parents[1] / "data" / "secrets" / "groq.dpapi"


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]


def _crypt(value: bytes, decrypt=False) -> bytes:
    if os.name != "nt":
        raise RuntimeError("DPAPI is available on Windows only; use GROQ_API_KEY elsewhere.")
    source = ctypes.create_string_buffer(value)
    incoming = Blob(len(value), ctypes.cast(source, ctypes.POINTER(ctypes.c_byte)))
    outgoing = Blob()
    crypt = ctypes.windll.crypt32
    if decrypt:
        success = crypt.CryptUnprotectData(
            ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)
        )
    else:
        success = crypt.CryptProtectData(
            ctypes.byref(incoming), "ArchimedesAI Groq", None, None, None, 1, ctypes.byref(outgoing)
        )
    if not success:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        ctypes.windll.kernel32.LocalFree(outgoing.data)


def store_groq(value: str):
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_bytes(_crypt(value.encode()))


def load_groq() -> str | None:
    return (
        _crypt(STORE.read_bytes(), decrypt=True).decode()
        if os.name == "nt" and STORE.exists()
        else None
    )
