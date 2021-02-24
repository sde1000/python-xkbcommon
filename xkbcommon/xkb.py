import enum
import mmap
import functools

from xkbcommon._ffi import ffi, lib

class _keepref:
    """Function wrapper that keeps a reference to another object."""
    def __init__(self, ref, func):
        self.ref = ref
        self.func = func

    def __call__(self, *args, **kwargs):
        self.func(*args, **kwargs)

class XKBError(Exception):
    """Base for all XKB exceptions"""
    pass

class XKBPathError(Exception):
    """There was a problem altering the include path of a Context."""
    pass

class XKBBufferTooSmall(XKBError):
    """A buffer created for libxkbcommon to return data in was too small.

    This is a limit in python-xkbcommon.  If you run into it, please
    file a bug report and the limit can be raised.
    """
    pass

class XKBInvalidKeysym(XKBError):
    pass

class XKBKeymapCreationFailure(XKBError):
    """Unable to create a keymap."""
    pass

class XKBKeymapReadError(XKBError):
    """Unable to fetch a keymap as a string."""
    pass

class XKBInvalidModifierIndex(XKBError):
    pass

class XKBModifierDoesNotExist(XKBError):
    """A given modifier name does not exist.

    If the name is one of a list of names and libxkbcommon does not
    indicate which of the list does not exist, modifier_name will be
    None.
    """
    def __init__(self, modifier_name):
        super().__init__(modifier_name)
        self.modifier_name = modifier_name

class XKBInvalidLayoutIndex(XKBError):
    pass

class XKBLayoutDoesNotExist(XKBError):
    def __init__(self, index_name):
        super().__init__(index_name)
        self.index_name = index_name

class XKBInvalidLEDIndex(XKBError):
    pass

class XKBLEDDoesNotExist(XKBError):
    def __init__(self, led_name):
        super().__init__(led_name)
        self.led_name = led_name

# Internal helper for logging callback
def _onerror_do_nothing(exception, exc_value, traceback):
    return
@ffi.def_extern(onerror=_onerror_do_nothing)
def _log_handler(user_data, level, message):
    context = ffi.from_handle(user_data)
    if context._log_fn:
        context._log_fn(context, level, ffi.string(message).decode('utf8'))

# Internal helper for keycode iteration
@ffi.def_extern(onerror=_onerror_do_nothing)
def _key_for_each_helper(keymap, key, data):
    l = ffi.from_handle(data)
    l.append(key)

# Keysyms http://xkbcommon.org/doc/current/group__keysyms.html

def keysym_get_name(keysym):
    "Get the name of a keysym."
    name = ffi.new("char[64]")
    r = lib.xkb_keysym_get_name(keysym, name, len(name))
    if r == -1:
        raise XKBInvalidKeysym()
    if r > len(name):
        raise XKBBufferTooSmall()
    return ffi.string(name).decode('ascii')

def keysym_from_name(name, case_insensitive=False):
    "Get a keysym from its name."
    flags = 0
    if case_insensitive:
        flags = flags | lib.XKB_KEYSYM_CASE_INSENSITIVE
    return lib.xkb_keysym_from_name(name.encode('ascii'), flags)

def keysym_to_string(keysym):
    buffer = ffi.new("char[64]")
    r = lib.xkb_keysym_to_utf8(keysym, buffer, len(buffer))
    if r == -1:
        raise XKBBufferTooSmall()
    if r == 0:
        return
    return ffi.string(buffer).decode('utf8')

# Library Context http://xkbcommon.org/doc/current/group__context.html

class Context:
    """xkbcommon library context.

    Every keymap compilation request must have a context associated
    with it. The context keeps around state such as the include path.

    The user may set some environment variables which affect the
    library:

    XKB_CONFIG_ROOT, HOME - affect include paths
    XKB_LOG_LEVEL - see set_log_level().
    XKB_LOG_VERBOSITY - see set_log_verbosity().
    XKB_DEFAULT_RULES
    XKB_DEFAULT_MODEL
    XKB_DEFAULT_LAYOUT
    XKB_DEFAULT_VARIANT
    XKB_DEFAULT_OPTIONS - see xkb_rule_names.
    """

    def __init__(self, no_default_includes=False, no_environment_names=False):
        """Create a new context.

        Keyword arguments:

        no_default_includes: if set, create this context with an empty
        include path.

        no_environment_names: if set, don't take RMLVO names from the
        environment.
        """
        flags = lib.XKB_CONTEXT_NO_FLAGS
        if no_default_includes:
            flags = flags | lib.XKB_CONTEXT_NO_DEFAULT_INCLUDES
        if no_environment_names:
            flags = flags | lib.XKB_CONTEXT_NO_ENVIRONMENT_NAMES
        context = lib.xkb_context_new(flags)
        if not context:
            raise XKBError("Couldn't create XKB context")
        self._context = ffi.gc(context, _keepref(lib, lib.xkb_context_unref))
        self._log_fn = None
        # We keep a reference to the handle to keep it alive
        self._userdata = ffi.new_handle(self)
        lib.xkb_context_set_user_data(self._context, self._userdata)

    # Include Paths http://xkbcommon.org/doc/current/group__include-path.html

    def include_path_append(self, path):
        "Append a new entry to the context's include path."
        r = lib.xkb_context_include_path_append(
            self._context, path.encode('utf8'))
        if r != 1:
            raise XKBPathError("Failed to append to include path")

    def include_path_append_default(self):
        "Append the default include paths to the context's include path."
        r = lib.xkb_context_include_path_append_default(self._context)
        if r != 1:
            raise XKBPathError("Failed to append default include paths")

    def include_path_reset_defaults(self):
        """Reset the context's include path to the default.

        Removes all entries from the context's include path, and
        inserts the default paths.
        """
        r = lib.xkb_context_include_path_reset_defaults(self._context)
        if r != 1:
            raise XKBPathError("Failed to restore default include path")

    def include_path_get(self, index):
        """Get a specific include path from the context's include path.

        Returns the include path at the specified index.  If the index
        is invalid, returns None.
        """
        assert isinstance(index, int)
        r = lib.xkb_context_include_path_get(self._context, index)
        if r:
            return ffi.string(r).decode("utf8")

    def num_include_paths(self):
        """Return the number of include paths"""
        return lib.xkb_context_num_include_paths(self._context)
        
    def include_path(self):
        "Iterate over the include path."
        i = 0
        while True:
            p = self.include_path_get(i)
            if not p:
                return
            yield p
            i += 1

    # Logging Handling http://xkbcommon.org/doc/current/group__logging.html

    def set_log_level(self, level):
        """Set the current logging level.

        The default level is XKB_LOG_LEVEL_ERROR. The environment
        variable XKB_LOG_LEVEL, if set at the time the context was
        created, overrides the default value.  It may be specified as
        a level number or name.
        """
        lib.xkb_context_set_log_level(self._context, level)

    def get_log_level(self):
        """Return the current logging level."""
        return lib.xkb_context_get_log_level(self._context)

    def set_log_verbosity(self, verbosity):
        """Set the current logging verbosity.

        The library can generate a number of warnings which are not
        helpful to ordinary users of the library. The verbosity may be
        increased if more information is desired (e.g. when developing
        a new keymap).

        The default verbosity is 0. The environment variable
        XKB_LOG_VERBOSITY, if set at the time the context was created,
        overrides the default value.

        Currently used values are 1 to 10, higher values being more
        verbose.  0 would result in no verbose messages being logged.

        Most verbose messages are of level XKB_LOG_LEVEL_WARNING or lower.
        """
        lib.xkb_context_set_log_verbosity(self._context, verbosity)

    def get_log_verbosity(self):
        """Return the current logging verbosity."""
        return lib.xkb_context_get_log_verbosity(self._context)

    def set_log_fn(self, handler):
        """Set a custom function to handle logging messages.

        By default, log messages from this library are printed to
        stderr. This function allows you to replace the default
        behavior with a custom handler. The handler is only called
        with messages which match the current logging level and
        verbosity settings for the context.

        The handler is called with the following arguments:
        - context: this object
        - level: the logging level of the message
        - message: the message itself

        Passing None as the handler restores the default function,
        which logs to stderr.

        NB this implementation uses xkb_context_set_user_data() on the
        context.  Don't call xkb_context_set_user_data() if you intend
        to install a custom function to handle logging messages.
        """
        if handler:
            lib._set_log_handler_internal(self._context)
            self._log_fn = handler
        else:
            lib.xkb_context_set_log_fn(self._context, ffi.NULL)

    # Keymap Creation http://xkbcommon.org/doc/current/group__keymap.html

    def keymap_new_from_names(self, rules=None, model=None, layout=None,
                              variant=None, options=None):
        """Create a keymap from RMLVO names.

        The primary keymap entry point: creates a new XKB keymap from
        a set of RMLVO (Rules + Model + Layouts + Variants + Options)
        names.

        Returns a Keymap compiled according to the RMLVO names, or
        None if the compilation failed.
        """
        # CFFI memory management note:
        # The C strings allocated below using ffi.new("char[]", ...)
        # are automatically deallocated when there are no remaining
        # python references to them. Being assigned to members of the
        # 'names' struct does not count as a reference! We keep
        # references to them in the 'keep_alive' list until after the
        # call to xkb_keymap_new_from_names() to avoid problems with
        # use-after-free.
        names = ffi.new("struct xkb_rule_names *")
        keep_alive = []
        for x in ("rules", "model", "layout", "variant", "options"):
            if locals()[x]:
                c = ffi.new("char[]", locals()[x].encode())
                setattr(names, x, c)
                keep_alive.append(c)
        r = lib.xkb_keymap_new_from_names(
            self._context, names, lib.XKB_KEYMAP_COMPILE_NO_FLAGS)
        del keep_alive, names
        if r == ffi.NULL:
            raise XKBKeymapCreationFailure(
                "xkb_keymap_new_from_names returned NULL")
        return Keymap(self, r, "names")

    # We can't call xkb_keymap_new_from_file directly because we have
    # no way to get a C stdio FILE * for a file opened by python.  We
    # can fake it by mmaping the file and using
    # xkb_keymap_new_from_{string,buffer} instead - which happens to
    # be what libxkbcommon does internally anyway!
    def keymap_new_from_file(self, file, format=lib.XKB_KEYMAP_FORMAT_TEXT_V1):
        "Create a Keymap from an open file"
        try:
            fn = file.fileno()
        except:
            load_method = "read_file"
            keymap = file.read()
            r = lib.xkb_keymap_new_from_string(
                self._context, keymap, format,
                lib.XKB_KEYMAP_COMPILE_NO_FLAGS)
        else:
            load_method = "mmap_file"
            mm = mmap.mmap(fn, 0)
            buf = ffi.from_buffer(mm)
            r = lib.xkb_keymap_new_from_buffer(
                self._context, buf, mm.size(), format,
                lib.XKB_KEYMAP_COMPILE_NO_FLAGS)
            del buf
            mm.close()

        if r == ffi.NULL:
            raise XKBKeymapCreationFailure(
                "xkb_keymap_new_from_buffer or xkb_keymap_new_from_string "
                "returned NULL")
        return Keymap(self, r, load_method)

    def keymap_new_from_string(
            self, string, format=lib.XKB_KEYMAP_FORMAT_TEXT_V1):
        "Create a Keymap from a keymap string."
        r = lib.xkb_keymap_new_from_string(
            self._context, string.encode("ascii"), format, lib.XKB_KEYMAP_COMPILE_NO_FLAGS)
        if r == ffi.NULL:
            raise XKBKeymapCreationFailure(
                "xkb_keymap_new_from_string returned NULL")
        return Keymap(self, r, "string")

    def keymap_new_from_buffer(
            self, buffer, format=lib.XKB_KEYMAP_FORMAT_TEXT_V1, length=None):
        "Create a Keymap from a memory buffer."
        buf = ffi.from_buffer(buffer)
        r = lib.xkb_keymap_new_from_buffer(
            self._context, buf, length if length else len(buf), format,
            lib.XKB_KEYMAP_COMPILE_NO_FLAGS)
        if r == ffi.NULL:
            raise XKBKeymapCreationFailure(
                "xkb_keymap_new_from_buffer returned NULL")
        return Keymap(self, r, "buffer")

class Keymap:
    """A keymap.

    Do not instantiate this object directly.  Instead, use the various
    'keymap_new_from_' methods of Context.
    """

    def __init__(self, context, pointer, load_method):
        self.load_method = load_method
        self._context = context

        self._keymap = ffi.gc(pointer, _keepref(lib, lib.xkb_keymap_unref))
        self._valid_keycodes = None

    def get_as_bytes(self, format=lib.XKB_KEYMAP_FORMAT_TEXT_V1):
        """Get the compiled keymap as bytes.

        On Python 3 will return a bytes object.

        On Python 2 will return a str object.
        """
        r = lib.xkb_keymap_get_as_string(self._keymap, format)
        if r == ffi.NULL:
            raise XKBKeymapReadError()
        kms = ffi.string(r)
        lib.free(r)
        return kms
        
    def get_as_string(self, format=lib.XKB_KEYMAP_FORMAT_TEXT_V1):
        """Get the compiled keymap as a string.

        On Python 3 will return a str object.

        On Python 2 will return a unicode object.
        """
        return self.get_as_bytes(format).decode('ascii')

    # Keymap Components http://xkbcommon.org/doc/current/group__components.html

    def min_keycode(self):
        "Get the minimum keycode in the keymap."
        return lib.xkb_keymap_min_keycode(self._keymap)

    def max_keycode(self):
        "Get the maximum keycode in the keymap."
        return lib.xkb_keymap_max_keycode(self._keymap)

    # The xkb_keymap_key_for_each() call isn't very amenable to being
    # used directly from python.  It's much more useful to implement a
    # python iterable instead.
    def _get_valid_keycodes(self):
        """Fetch a list of valid keycodes in the keymap.

        Uses the xkb_keymap_key_for_each() call.
        """
        keycodes = []
        keycode_ref = ffi.new_handle(keycodes)
        lib.xkb_keymap_key_for_each(
            self._keymap, lib._key_for_each_helper, keycode_ref)
        self._valid_keycodes = keycodes

    def __iter__(self):
        """Iterate over valid keycodes"""
        if self._valid_keycodes is None:
            self._get_valid_keycodes()
        return iter(self._valid_keycodes)

    def num_mods(self):
        """Get the number of modifiers in the keymap."""
        return lib.xkb_keymap_num_mods(self._keymap)

    def mod_get_name(self, idx):
        """Get the name of a modifier by index.

        Returns the name.  If the index is invalid, raises
        XKBInvalidModifierIndex.
        """
        r = lib.xkb_keymap_mod_get_name(self._keymap, idx)
        if r == ffi.NULL:
            raise XKBInvalidModifierIndex()
        return ffi.string(r).decode('ascii')

    def mod_get_index(self, name):
        """Get the index of a modifier by name.

        Returns the index.  If no modifier with this name exists,
        raises XKBModifierDoesNotExist.
        """
        r = lib.xkb_keymap_mod_get_index(self._keymap, name.encode('ascii'))
        if r == lib.XKB_MOD_INVALID:
            raise XKBModifierDoesNotExist(name)
        return r

    def num_layouts(self):
        """Get the number of layouts in the keymap."""
        return lib.xkb_keymap_num_layouts(self._keymap)

    def layout_get_name(self, idx):
        """Get the name of a layout by index.

        Returns the name.  If the layout does not have a name, returns
        None.  If the index is invalid, raises XKBInvalidLayoutIndex.
        """
        if idx >= self.num_layouts():
            raise XKBInvalidLayoutIndex()
        r = lib.xkb_keymap_layout_get_name(self._keymap, idx)
        if r == ffi.NULL:
            return
        return ffi.string(r).decode('ascii')

    def layout_get_index(self, name):
        """Get the index of a layout by name.

        Returns the index.  If no layout exists with this name, raises
        XKBLayoutDoesNotExist. If more than one layout in the keymap
        has this name, returns the lowest index among them.
        """
        r = lib.xkb_keymap_layout_get_index(self._keymap, name.encode('ascii'))
        if r == lib.XKB_LAYOUT_INVALID:
            raise XKBLayoutDoesNotExist(name)
        return r

    def num_leds(self):
        """Get the number of LEDs in the keymap.

        Warning: The range [ 0..Keymap.num_leds() ) includes all of
        the LEDs in the keymap, but may also contain inactive
        LEDs. When iterating over this range, you need to handle this
        case when calling functions such as Keymap.led_get_name()
        or State.led_index_is_active().
        """
        return lib.xkb_keymap_num_leds(self._keymap)

    def led_get_name(self, idx):
        """Get the name of a LED by index.

        Returns the name. If the index is invalid, returns None.
        """
        r = lib.xkb_keymap_led_get_name(self._keymap, idx)
        if r == ffi.NULL:
            raise XKBInvalidLEDIndex()
        return ffi.string(r).decode('ascii')

    def led_get_index(self, name):
        """Get the index of a LED by name.

        Returns the index. If no LED with this name exists, returns
        lib.XKB_LED_INVALID.
        """
        r = lib.xkb_keymap_led_get_index(self._keymap, name.encode('ascii'))
        if r == lib.XKB_LED_INVALID:
            raise XKBLEDDoesNotExist(name)
        return r

    def num_layouts_for_key(self, key):
        """Get the number of layouts for a specific key.

        This number can be different from Keymap.num_layouts(), but is
        always smaller. It is the appropriate value to use when
        iterating over the layouts of a key.
        """
        return lib.xkb_keymap_num_layouts_for_key(self._keymap, key)

    def num_levels_for_key(self, key, layout):
        """Get the number of shift levels for a specific key and layout.

        If layout is out of range for this key (that is, larger or
        equal to the value returned by Keymap.num_layouts_for_key()),
        it is brought back into range in a manner consistent with
        State.key_get_layout().
        """
        return lib.xkb_keymap_num_levels_for_key(self._keymap, key, layout)

    def key_get_syms_by_level(self, key, layout, level):
        """Get the keysyms obtained from pressing a key in a given layout and
        shift level.

        This function is like State.key_get_syms(), only the layout
        and shift level are not derived from the keyboard state but
        are instead specified explicitly.

        Returns a list of keysyms.
        """
        syms_out = ffi.new("const xkb_keysym_t **")
        r = lib.xkb_keymap_key_get_syms_by_level(
            self._keymap, key, layout, level, syms_out)
        syms = []
        if r > 0:
            assert syms_out[0] != ffi.NULL
        for i in range(0, r):
            syms.append(syms_out[0][i])
        return syms

    def key_repeats(self, key):
        """Determine whether a key should repeat or not.

        A keymap may specify different repeat behaviors for different
        keys. Most keys should generally exhibit repeat behavior; for
        example, holding the 'a' key down in a text editor should
        normally insert a single 'a' character every few milliseconds,
        until the key is released. However, there are keys which
        should not or do not need to be repeated. For example,
        repeating modifier keys such as Left/Right Shift or Caps Lock
        is not generally useful or desired.

        Returns True if the key should repeat, False otherwise.
        """
        return lib.xkb_keymap_key_repeats(self._keymap, key) == 1

    # Keyboard State http://xkbcommon.org/doc/current/group__state.html
    
    def state_new(self):
        """Create a new keyboard state object.

        Returns a new keyboard state object.  Raises XKBError on
        failure.
        """
        return KeyboardState(self)


@enum.unique
class KeyDirection(enum.IntEnum):
    XKB_KEY_UP = lib.XKB_KEY_UP
    XKB_KEY_DOWN = lib.XKB_KEY_DOWN


XKB_KEY_UP = KeyDirection.XKB_KEY_UP
XKB_KEY_DOWN = KeyDirection.XKB_KEY_DOWN


@enum.unique
class StateComponent(enum.IntFlag):
    "An integer corresponding to enum xkb_state_component"
    XKB_STATE_MODS_DEPRESSED = lib.XKB_STATE_MODS_DEPRESSED
    XKB_STATE_MODS_LATCHED = lib.XKB_STATE_MODS_LATCHED
    XKB_STATE_MODS_LOCKED = lib.XKB_STATE_MODS_LOCKED
    XKB_STATE_MODS_EFFECTIVE = lib.XKB_STATE_MODS_EFFECTIVE
    XKB_STATE_LAYOUT_DEPRESSED = lib.XKB_STATE_LAYOUT_DEPRESSED
    XKB_STATE_LAYOUT_LATCHED = lib.XKB_STATE_LAYOUT_LATCHED
    XKB_STATE_LAYOUT_LOCKED = lib.XKB_STATE_LAYOUT_LOCKED
    XKB_STATE_LAYOUT_EFFECTIVE = lib.XKB_STATE_LAYOUT_EFFECTIVE
    XKB_STATE_LEDS = lib.XKB_STATE_LEDS

for _sc in StateComponent:
    globals()[_sc.name] = _sc

@enum.unique
class StateMatch(enum.IntFlag):
    "An integer corresponding to enum xkb_state_match"
    XKB_STATE_MATCH_ANY = lib.XKB_STATE_MATCH_ANY
    XKB_STATE_MATCH_ALL = lib.XKB_STATE_MATCH_ALL
    XKB_STATE_MATCH_NON_EXCLUSIVE = lib.XKB_STATE_MATCH_NON_EXCLUSIVE

for _sc in StateMatch:
    globals()[_sc.name] = _sc

class KeyboardState:
    def __init__(self, keymap):
        state = lib.xkb_state_new(keymap._keymap)
        if not state:
            raise XKBError("Couldn't create keyboard state")
        # Keep the keymap around to ensure it isn't collected too soon
        self.keymap = keymap
        self._state = ffi.gc(state, _keepref(lib, lib.xkb_state_unref))

    def get_keymap(self):
        """Get the Keymap which a keyboard state object is using.

        The keymap is also accessible as the "keymap" attribute.
        """
        return self.keymap

    def update_key(self, key, direction):
        """Update the keyboard state to reflect a given key being pressed or
        released.

        This entry point is intended for programs which track the
        keyboard state explictly (like an evdev client). If the state
        is serialized to you by a master process (like a Wayland
        compositor) using functions like KeyboardState.serialize_mods(),
        you should use KeyboardState.update_mask() instead. The two
        functions should not generally be used together.

        A series of calls to this function should be consistent; that
        is, a call with XKB_KEY_DOWN for a key should be matched by an
        XKB_KEY_UP; if a key is pressed twice, it should be released
        twice; etc. Otherwise (e.g. due to missed input events),
        situations like "stuck modifiers" may occur.

        This function is often used in conjunction with the function
        KeyboardState.key_get_syms() (or
        KeyboardState.key_get_one_sym()), for example, when handling a
        key event. In this case, you should prefer to get the keysyms
        before updating the key, such that the keysyms reported for
        the key event are not affected by the event itself. This is
        the conventional behavior.

        Returns a mask of state components that have changed as a
        result of the update. If nothing in the state has changed,
        returns 0.
        """
        return StateComponent(
            lib.xkb_state_update_key(self._state, key, direction))
                                        
    def update_mask(self, depressed_mods, latched_mods, locked_mods,
                    depressed_layout, latched_layout, locked_layout):
        """Update a keyboard state from a set of explicit masks.

        This entry point is intended for window systems and the like,
        where a master process holds an xkb_state, then serializes it
        over a wire protocol, and clients then use the serialization
        to feed in to their own xkb_state.

        All parameters must always be passed, or the resulting state
        may be incoherent.

        The serialization is lossy and will not survive round trips;
        it must only be used to feed slave state objects, and must not
        be used to update the master state.

        If you do not fit the description above, you should use
        KeyboardState.update_key() instead. The two functions should
        not generally be used together.

        Returns a mask of state components that have changed as a
        result of the update. If nothing in the state has changed,
        returns 0.
        """
        return StateComponent(lib.xkb_state_update_mask(
            self._state, depressed_mods, latched_mods, locked_mods,
            depressed_layout, latched_layout, locked_layout))

    def key_get_syms(self, key):
        """Get the keysyms obtained from pressing a particular key in a given
        keyboard state.

        Get the keysyms for a key according to the current active
        layout, modifiers and shift level for the key, as determined
        by a keyboard state.

        As an extension to XKB, this function can return more than one
        keysym. If you do not want to handle this case, you can use
        KeyboardState.key_get_one_sym() for a simpler interface.

        This function does not perform any Keysym
        Transformations. (This might change).
        """
        syms_out = ffi.new("const xkb_keysym_t **")
        r = lib.xkb_state_key_get_syms(self._state, key, syms_out)
        syms = []
        if r > 0:
            assert syms_out[0] != ffi.NULL
        for i in range(0, r):
            syms.append(syms_out[0][i])
        return syms
        
    def key_get_string(self, key):
        """Get the Unicode/UTF-8 string obtained from pressing a particular
        key in a given keyboard state.

        This function performs Capitalization and Control Keysym
        Transformations.

        Returns the string.  If there is nothing to return, returns
        the empty string.
        """
        buffer = ffi.new("char[64]")
        r = lib.xkb_state_key_get_utf8(self._state, key, buffer, len(buffer))
        if r + 1 > len(buffer):
            raise XKBBufferTooSmall()
        return ffi.string(buffer).decode('utf8')

    def key_get_one_sym(self, keycode):
        """Get the single keysym obtained from pressing a particular key in a
        given keyboard state.

        This function is similar to xkb_state_key_get_syms(), but
        intended for users which cannot or do not want to handle the
        case where multiple keysyms are returned (in which case this
        function is preferred).

        This function performs Capitalization Keysym Transformations.

        Returns the keysym. If the key does not have exactly one
        keysym, returns lib.XKB_KEY_NoSymbol.
        """
        return lib.xkb_state_key_get_one_sym(self._state, keycode)

    def key_get_layout(self, key):
        """Get the effective layout index for a key in a given keyboard state.

        Returns the layout index for the key in the given keyboard
        state. If the given keycode is invalid, or if the key is not
        included in any layout at all, raises XKBInvalidLayoutIndex.
        """
        r = lib.xkb_state_key_get_layout(self._state, key)
        if r == lib.XKB_LAYOUT_INVALID:
            raise XKBInvalidLayoutIndex()
        return r

    def key_get_level(self, key, layout):
        """Get the effective shift level for a key in a given keyboard state
        and layout.

        layout must be smaller than:
        State.get_keymap().num_layouts_for_key(key) 

        Usually layout would be:
        State.key_get_layout(key) 

        Returns the shift level index. If the key or layout are
        invalid, raises XKBInvalidLayoutIndex.
        """
        r = lib.xkb_state_key_get_level(self._state, key, layout)
        if r == lib.XKB_LEVEL_INVALID:
            raise XKBInvalidLayoutIndex()
        return r

    def serialize_mods(self, components):
        """The counterpart to xkb_state_update_mask for modifiers, to be used
        on the server side of serialization.

        components is a mask of the modifier state components to
        serialize. State components other than XKB_STATE_MODS_* are
        ignored. If XKB_STATE_MODS_EFFECTIVE is included, all other
        state components are ignored.

        Returns a xkb_mod_mask_t representing the given components of
        the modifier state.

        This function should not be used in regular clients; please
        use the State.mod_*_is_active() API instead.
        """
        return lib.xkb_state_serialize_mods(self._state, components)

    def serialize_layout(self, components):
        """The counterpart to xkb_state_update_mask for layouts, to be used on
        the server side of serialization.

        components is a mask of the modifier state components to
        serialize. State components other than XKB_STATE_MODS_* are
        ignored. If XKB_STATE_MODS_EFFECTIVE is included, all other
        state components are ignored.

        Returns a layout index representing the given components of
        the layout state.

        This function should not be used in regular clients; please
        use the State.layout_*_is_active() API instead.
        """
        return lib.xkb_state_serialize_layout(self._state, components)

    def mod_name_is_active(self, name, type):
        """Test whether a modifier is active in a given keyboard state by
        name.

        type is the component of the state against which to match the
        given modifiers.

        Returns True if the modifier is active, False if it is not.
        If the modifier name does not exist in the keymap, raises
        XKBModifierDoesNotExist.
        """
        r = lib.xkb_state_mod_name_is_active(self._state, name.encode(), type)
        if r == -1:
            raise XKBModifierDoesNotExist(name)
        return r == 1

    def mod_names_are_active(self, type, match, names):
        """Test whether a set of modifiers are active in a given keyboard
        state by name.

        type is the component of the state against which to match the
        given modifiers.

        match is the manner by which to match the state against the
        given modifiers.

        names is an iterable of modifier names to test.

        Returns True if the modifiers are active, False if they are
        not.  If any of the modifier names do not exist, raises
        XKBModifierDoesNotExist(None).
        """
        args = [ffi.new("char []", n.encode('ascii')) for n in names]
        args.append(ffi.NULL)
        r = lib.xkb_state_mod_names_are_active(self._state, type, match, *args)
        if r == -1:
            raise XKBModifierDoesNotExist(None)
        return r == 1

    def mod_index_is_active(self, idx, type):
        """Test whether a modifier is active in a given keyboard state by
        index.

        Returns True if the modifier is active, False if it is not.
        If the modifier index is invalid in the keymap, raises
        XKBInvalidModifierIndex.
        """
        r = lib.xkb_state_mod_index_is_active(self._state, idx, type)
        if r == -1:
            raise XKBInvalidModifierIndex()
        return r == 1

    def mod_indices_are_active(self, type, match, mods):
        """Test whether a set of modifiers are active in a given keyboard
        state by index.

        type is the component of the state against which to match the
        given modifiers.

        match is the manner by which to match the state against the
        given modifiers.

        mods is an iterable of modifier indices to test.

        Returns True if the modifiers are active, False if they are
        not.  If any of the modifier indices are invalid in the
        keymap, raises XKBInvalidModifierIndex.
        """
        args = [ffi.cast("int", x) for x in mods]
        args.append(ffi.cast("int", lib.XKB_MOD_INVALID))
        r = lib.xkb_state_mod_indices_are_active(self._state, type, match, *args)
        if r == -1:
            raise XKBInvalidModifierIndex()
        return r == 1

    def mod_index_is_consumed(self, key, idx):
        """Test whether a modifier is consumed by keyboard state translation
        for a key.

        Returns True if the modifier is consumed, False if it is not.
        If the modifier index is not valid in the keymap, raises
        XKBInvalidModifierIndex.
        """
        r = lib.xkb_state_mod_index_is_consumed(self._state, key, idx)
        if r == -1:
            raise XKBInvalidModifierIndex()
        return r == 1

    def mod_mask_remove_consumed(self, key, mask):
        """Remove consumed modifiers from a modifier mask for a key.

        Takes the given modifier mask, and removes all modifiers which
        are consumed for that particular key.
        """
        return lib.xkb_state_mod_mask_remove_consumed(self._state, key, mask)

    def key_get_consumed_mods(self, key):
        """Get the mask of modifiers consumed by translating a given key.

        Returns a mask of the consumed modifiers.
        """
        return lib.xkb_state_key_get_consumed_mods(self._state, key)

    def layout_name_is_active(self, name, type):
        """Test whether a layout is active in a given keyboard state by name.

        Returns True if the layout is active, False if it is not.  If
        no layout with this name exists in the keymap, raises
        XKBLayoutDoesNotExist.

        If multiple layouts in the keymap have this name, the one with
        the lowest index is tested.
        """
        r = lib.xkb_state_layout_name_is_active(self._state, name.encode(), type)
        if r == -1:
            raise XKBLayoutDoesNotExist(name)
        return r == 1

    def layout_index_is_active(self, idx, type):
        """Test whether a layout is active in a given keyboard state by index.

        Returns True if the layout is active, False if it is not.  If
        the layout index is not valid in the keymap, raises
        XKBInvalidLayoutIndex.
        """
        r = lib.xkb_state_layout_index_is_active(self._state, idx, type)
        if r == -1:
            raise XKBInvalidLayoutIndex()
        return r == 1

    def led_name_is_active(self, name):
        """Test whether a LED is active in a given keyboard state by name.

        Returns True if the LED is active, False if it is not.  If no
        LED with this name exists in the keymap, raises
        XKBLEDDoesNotExist.
        """
        r = lib.xkb_state_led_name_is_active(self._state, name.encode('ascii'))
        if r == -1:
            raise XKBLEDDoesNotExist(name)
        return r == 1

    def led_index_is_active(self, idx):
        """Test whether a LED is active in a given keyboard state by index.

        Returns True if the LED is active, False if it is not.  If the
        LED index is not valid in the keymap, raises
        XKBInvalidLEDIndex.
        """
        r = lib.xkb_state_led_index_is_active(self._state, idx)
        if r == -1:
            raise XKBInvalidLEDIndex()
        return r == 1
