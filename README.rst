xkbcommon
=========

Python bindings for libxkbcommon_ using cffi_.

Example usage:

>>> from xkbcommon import xkb
>>> ctx = xkb.Context()
>>> keymap = ctx.keymap_new_from_names()
>>> state = keymap.state_new()
>>> state.led_name_is_active("Caps Lock")
False
>>> capslock = 66
>>> str(state.update_key(capslock, xkb.XKB_KEY_DOWN))
'StateComponent.XKB_STATE_MODS_DEPRESSED|XKB_STATE_MODS_LOCKED|XKB_STATE_MODS_EFFECTIVE|XKB_STATE_LEDS'
>>> str(state.update_key(capslock, xkb.XKB_KEY_UP))
'StateComponent.XKB_STATE_MODS_DEPRESSED'
>>> state.led_name_is_active("Caps Lock")
True

Version numbering
-----------------

From release 0.5 onwards, the version numbering of this package will
relate to releases of libxkbcommon_ as follows:

If the Python package version is major.minor[.patch] then it requires
at least release major.minor.0 of libxkbcommon to build and run, and
should work with any subsequent release. The patch version of the
Python package is unrelated to the patch version of libxkbcommon.

In practice this means that **you should always specify a maximum
version when depending on xkbcommon**.

* Most users should specify ``xkbcommon<1.1``

* If you need to use ``xkb.Context(no_secure_getenv=True)`` then
  specify ``xkbcommon<1.6``

* If you need to iterate over an ``xkb.ComposeTable`` instance then
  specify ``xkbcommon<1.7``

.. _libxkbcommon: https://xkbcommon.org/
.. _cffi: https://pypi.python.org/pypi/cffi
