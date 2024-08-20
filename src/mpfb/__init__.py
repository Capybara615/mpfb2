"""This is the main file for MPFB. For more information, see the README.md file in the zip."""

fake_bl_info = {  # pylint: disable=C0103
    "name": "mpfb",
    "author": "Joel Palmius",
    "version": (2, 0, 5),
    "blender": (4, 2, 0),
    "location": "View3D > Properties > MPFB",
    "description": "Free and open source human character editor",
    "doc_url": "http://static.makehumancommunity.org/mpfb.html",
    "tracker_url": "https://github.com/makehumancommunity/mpfb2/issues",
    "category": "MakeHuman"}

# These are constants that can be imported from submodules
VERSION = fake_bl_info["version"]
BUILD_INFO = "FROM_SOURCE"

# Don't import this log object. Instead, get a local logger via LogService
_LOG = None

# WARNING!!!
# Do not try to import anything from anywhere outside of the register method.
# We can only rely on singletons in the rest of the module being initialized
# and available once blender has gotten far enough as to call register.
#
# Because of this we will also disable pylint's warning about these imports
# pylint: disable=C0415
#
# We will also disable warnings about unused imports, since the point of
# importing here is to just make sure everything is up and running
# pylint: disable=W0611

import bpy, os, sys, traceback
from bpy.utils import register_class

_OLD_EXCEPTHOOK = None

# For printing output before _LOG has been initialized
_DEBUG = False


def log_crash(type, value, tb):
    global _OLD_EXCEPTHOOK
    stacktrace = "\n"
    for line in traceback.extract_tb(tb).format():
        stacktrace = stacktrace + line
    _LOG.error("Unhandled crash", stacktrace + "\n" + str(value) + "\n")
    if _OLD_EXCEPTHOOK:
        _OLD_EXCEPTHOOK(type, value, tb)


def get_preference(name):
    global _DEBUG
    if _DEBUG:
        print("get_preference()")
    if __package__ in bpy.context.preferences.addons:
        mpfb = bpy.context.preferences.addons[__package__]
        if hasattr(mpfb, "preferences"):
            prefs = mpfb.preferences
            if hasattr(prefs, name):
                value = getattr(prefs, name)
                if _DEBUG:
                    print("Found addon preference", (name, value))
                return value
            print("There were addon preferences, but key did not exist:", name)
            print("preferences", dir(prefs))
            print("hasattr", hasattr(prefs, name))
            print("name in", name in prefs)
            return None
        print("The '" + __package__ + "' addon does not have any preferences!?")
        raise ValueError("Preferences have not been initialized properly")
    print("The '" + __package__ + "' addon does not exist!?")
    raise ValueError("I don't seem to exist")


ClassManager = None

MPFB_CONTEXTUAL_INFORMATION = None


def register():
    """At this point blender is ready enough for it to make sense to
    start initializing python singletons"""

    global _LOG  # pylint: disable=W0603
    global _OLD_EXCEPTHOOK  # pylint: disable=W0603

    # Preferences will be needed before starting the rest of the addon
    from ._preferences import MpfbPreferences
    try:
        register_class(MpfbPreferences)
    except:
        print("WARNING: Could not register preferences class. Maybe it was registered by an earlier version of MPFB?")

    from .services import LogService  # This will also cascade import the other services
    _LOG = LogService.get_logger("mpfb.init")
    _LOG.info("Build info", "FROM_SOURCE")
    _LOG.reset_timer()

    if get_preference("mpfb_excepthook"):
        _LOG.warn("Overriding the global exception handler. You should probably disable this when not needing it.")
        _OLD_EXCEPTHOOK = sys.excepthook
        sys.excepthook = log_crash

    # ClassManager is a singleton to which all modules can add their
    # Blender classes, preferably when the module is imported the first
    # time. Thus we'll import all packages which can theoretically
    # contain blender classes.

    from ._classmanager import ClassManager as _ClassManager
    global ClassManager
    ClassManager = _ClassManager

    if not ClassManager.isinitialized():
        classmanager = ClassManager()  # pylint: disable=W0612
        _LOG.debug("classmanager", classmanager)

    _LOG.debug("About to import mpfb.ui")
    from .ui import UI_DUMMY_VALUE  # pylint: disable=W0612

    _LOG.debug("After imports")

    # We can now assume all relevant classes have been added to the
    # class manager singleton.

    _LOG.debug("About to request class registration")
    ClassManager.register_classes()

    from .services import SystemService

    if SystemService.is_blender_version_at_least():
        _LOG.debug("About to check if MakeHuman is online")

        # Try to find out where the makehuman user data is at
        from .services import LocationService, SocketService
        if LocationService.is_mh_auto_user_data_enabled():
            mh_user_dir = None
            try:
                mh_user_dir = SocketService.get_user_dir()
                _LOG.info("Socket service says makeHuman user dir is at", mh_user_dir)
                if mh_user_dir and os.path.exists(mh_user_dir):
                    mh_user_data = os.path.join(mh_user_dir, "data")
                    LocationService.update_mh_user_data_if_relevant(mh_user_data)
            except ConnectionRefusedError as err:
                _LOG.error("Could not read mh_user_dir. Maybe socket server is down? Error was:", err)
                mh_user_dir = None

    # To allow other code structures (primarily the unit test code) access to MPFB's logic without knowing
    # anything about the module structure, we will provide some contextual information.
    global MPFB_CONTEXTUAL_INFORMATION
    MPFB_CONTEXTUAL_INFORMATION = dict()
    MPFB_CONTEXTUAL_INFORMATION["__package__"] = __package__
    MPFB_CONTEXTUAL_INFORMATION["__file__"] = __file__

    from .services import SERVICES
    MPFB_CONTEXTUAL_INFORMATION["SERVICES"] = SERVICES

    # One might have assumed that bpy.app.driver_namespace would be good place to store this, but that gets wiped
    # when loading a new blend file. Instead something like the following is needed:
    #
    # import importlib
    # for amod in sys.modules:
    #    if amod.endswith("mpfb"):
    #        mpfb_mod = importlib.import_module(amod)
    #        print(mpfb_mod.MPFB_CONTEXTUAL_INFORMATION)
    #
    # Sample usage of this can be seen in test/tests/__init__.py

    _LOG.time("Number of milliseconds to run entire register() method:")
    _LOG.info("MPFB initialization has finished.")


def unregister():
    """Deconstruct all loaded blenderish classes"""

    global _LOG  # pylint: disable=W0603

    _LOG.debug("About to unregister classes")
    global ClassManager
    ClassManager.unregister_classes()


__all__ = ["VERSION", "BUILD_INFO", "ClassManager"]

