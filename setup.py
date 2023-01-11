from setuptools import setup

setup(
    cffi_modules=["xkbcommon/ffi_build.py:ffibuilder"],
)
