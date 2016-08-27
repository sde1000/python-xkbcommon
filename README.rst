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
'XKB_STATE_MODS_DEPRESSED|XKB_STATE_MODS_LOCKED|XKB_STATE_MODS_EFFECTIVE|XKB_STATE_LEDS'
>>> str(state.update_key(capslock, xkb.XKB_KEY_UP))
'XKB_STATE_MODS_DEPRESSED'
>>> state.led_name_is_active("Caps Lock")
True

.. _libxkbcommon: http://xkbcommon.org/
.. _cffi: https://pypi.python.org/pypi/cffi
