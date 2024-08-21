"""Functionality for logging and profiling"""

import os, bpy, time, pprint, inspect, json
from .. import get_preference, DEBUG

# There's a catch 22 where paths should be read from the location
# service, but the location service is dependent on the log service

_OVERRIDDEN_HOME = None

try:
    _OVERRIDDEN_HOME = get_preference("mpfb_user_data")
except:
    print("Could not read preference mpfb_user_data")

_BPYHOME = bpy.utils.resource_path('USER')  # pylint: disable=E1111
if _OVERRIDDEN_HOME is None or not _OVERRIDDEN_HOME:
    _MPFBHOME = os.path.join(_BPYHOME, "mpfb")
else:
    _MPFBHOME = _OVERRIDDEN_HOME

_LOGDIR = os.path.abspath(os.path.join(_MPFBHOME, "logs"))
_COMBINED = os.path.join(_LOGDIR, "combined.txt")
_CONFIG_DIR = os.path.join(_MPFBHOME, "config")
_CONFIG = os.path.join(_CONFIG_DIR, "log_levels.json")

if DEBUG:
    print("\nInitializing MPFB log service. Logs can be found in " + str(_LOGDIR) + "\n")

if not os.path.exists(_LOGDIR):
    os.makedirs(_LOGDIR, exist_ok=True)

if not os.path.exists(_CONFIG_DIR):
    os.makedirs(_CONFIG_DIR, exist_ok=True)

_JUSTIFICATION = 40
_START = int(time.time() * 1000.0)


class Logger():

    """The Logger class is used to create log channels that can log messages at different severity levels. 
    Each log channel writes messages to its own file and also to a combined log file. The log levels allow 
    filtering of messages so that only those of a certain severity or higher are logged. This is useful for
    debugging and monitoring the behavior of the application."""

    def __init__(self, name, level=5):
        """Construct a new log channel."""
        self.name = name
        self.level = level
        self.level_is_overridden = False
        self.path = os.path.join(_LOGDIR, "separated." + name + ".txt")
        self.time_stamp = _START
        with open(self.path, "w", encoding="utf-8") as log_file:
            log_file.write("")

    def _log_message(self, level, message, extra_object=None):
        if level <= self.level:
            extra = ""
            if not extra_object is None:
                extra = " " + str(extra_object)
            location = str(self.name + " ").ljust(_JUSTIFICATION, ".") + ": "
            long_message = "[" + LogService.LOGLEVELS[level] + "] " + location + message + extra
            short_message = "[" + LogService.LOGLEVELS[level] + "] " + message + extra
            print(long_message)
            with open(self.path, "a", encoding="utf-8") as log_file:
                log_file.write(short_message + "\n")
            with open(_COMBINED, "a", encoding="utf-8") as log_file:
                log_file.write(long_message + "\n")

    def debug_enabled(self):
        """Check if debug logging is enabled for this logger."""
        return self.level >= LogService.DEBUG

    def set_level(self, level):
        """Set the highest level to report for this channel"""
        self.level = level
        self.level_is_overridden = True

    def get_level(self):
        """Get the highest level to report for this channel."""
        return self.level

    def crash(self, message, extra_object=None):
        """Report a crash. This will always be reported, no matter what the log level is set to."""
        self._log_message(LogService.CRASH, message, extra_object)

    def error(self, message, extra_object=None):
        """Report an error, if the log level is at least 1."""
        self._log_message(LogService.ERROR, message, extra_object)

    def warn(self, message, extra_object=None):
        """Report a warning, if the log level is at least 2."""
        self._log_message(LogService.WARN, message, extra_object)

    def info(self, message, extra_object=None):
        """Report an information, if the log level is at least 3."""
        self._log_message(LogService.INFO, message, extra_object)

    def debug(self, message, extra_object=None):
        """Report a debug message, if the log level is at least 4."""
        self._log_message(LogService.DEBUG, message, extra_object)

    def trace(self, message, extra_object=None):
        """Report an trace message, if the log level is at least 5."""
        self._log_message(LogService.TRACE, message, extra_object)

    def dump(self, message, extra_object):
        """Dump a large data structure to the log, if the log level is at least trace."""
        if self.level > LogService.TRACE:
            if isinstance(extra_object, str):
                serialized_object = "\n" + extra_object
            else:
                serialized_object = "\n" + pprint.pformat(extra_object, 4, 180, depth=5)
            self._log_message(LogService.DUMP, message, serialized_object)

    def enter(self):
        """Report that a method was entered, if the log level is at least trace."""
        if self.level >= LogService.TRACE:
            info = dict()
            stack = inspect.currentframe().f_back
            info["line_number"] = str(stack.f_lineno)
            info["caller_name"] = stack.f_globals["__name__"]
            info["file_name"] = stack.f_globals["__file__"]
            info["caller_method"] = inspect.stack()[1][3]
            message = "Now entering {}.{}():{}".format(info["caller_name"], info["caller_method"], info["line_number"])
            self._log_message(LogService.TRACE, message)

    def get_current_time(self):
        """Return the number of millisections which has passed since time was last reset for this channel."""
        return int(time.time() * 1000.0) - self.time_stamp

    def time(self, message):
        """Report a timestamp message, if log level is at least debug."""
        current = int(time.time() * 1000.0)
        self._log_message(LogService.DEBUG, message, current - self.time_stamp)

    def reset_timer(self):
        """Reset the timer for this log channel"""
        self.time_stamp = int(time.time() * 1000.0)

    def get_path_to_log_file(self):
        """Return the absolute path to the log file for this logger."""
        return os.path.abspath(self.path)


class LogService():
    """Service for logging messages."""

    LOGLEVELS = ["CRASH", "ERROR", "WARN ", "INFO ", "DEBUG", "TRACE", "DUMP "]
    CRASH = 0
    ERROR = 1
    WARN = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5
    DUMP = 6  # For putting very large objects into log output

    def __init__(self):
        """Don't try to construct the LogService class. It only contains static methods."""
        raise RuntimeError("You should not instance LogService. Use its static methods instead.")

    @staticmethod
    def get_logger(name):
        """Get (or create) a log channel with the specified name."""
        return _LOGSERVICE.get_or_create_log_channel(str(name))

    @staticmethod
    def set_default_log_level(level):
        """Set the default level to use for channels, if no specific override has been set for that channel."""
        return _LOGSERVICE.set_default_log_level(level)

    @staticmethod
    def get_default_log_level():
        """Return the default log level."""
        return _LOGSERVICE.get_default_log_level()

    @staticmethod
    def get_loggers_list_as_property_enum(log_filter=""):
        """Return a list of loggers in a format which is appropriate for lists in the UI."""
        return _LOGSERVICE.get_loggers_list_as_property_enum(log_filter)

    @staticmethod
    def get_loggers_categories_as_property_enum():
        """Return a list of logger categories in a format which is appropriate for lists in the UI."""
        return _LOGSERVICE.get_loggers_categories_as_property_enum()

    @staticmethod
    def get_loggers():
        """Return a live dict with the currently defined loggers."""
        return _LOGSERVICE.get_loggers()

    @staticmethod
    def set_level_override(logger_name, level):
        """Specify a different level to use rather than the default for the specified logger."""
        _LOGSERVICE.set_level_override(logger_name, level)

    @staticmethod
    def reset_log_levels():
        """Reset all levels (including the default) to the factory settings."""
        _LOGSERVICE.reset_log_levels()

    @staticmethod
    def get_path_to_combined_log_file():
        """Return the absolute path to the combined log file."""
        return os.path.abspath(_COMBINED)


class _LogService():

    def __init__(self):
        self._loggers = dict()
        self._default_log_level = LogService.INFO
        self._level_overrides = dict()
        self._level_overrides["default"] = self._default_log_level
        if os.path.exists(_CONFIG):
            with open(_CONFIG, "r", encoding="utf-8") as json_file:
                self._level_overrides = json.load(json_file)
            if "default" in self._level_overrides:
                self._default_log_level = self._level_overrides["default"]
        else:
            print("Log config does not exist. Creating empty template.")
            self.rewrite_json()
        with open(_COMBINED, "w", encoding="utf-8") as log_file:
            log_file.write("")

    def get_default_log_level(self):
        """Return the default log level."""
        return self._default_log_level

    def reset_log_levels(self):
        """Reset all log levels to their default values.
        
        This method sets the default log level to INFO and clears any level overrides.
        It also updates the log configuration file and resets the log level for all existing loggers.
        """
        self._default_log_level = LogService.INFO
        self._level_overrides = dict()
        self._level_overrides["default"] = self._default_log_level
        self.rewrite_json()
        for logger in self._loggers.values():
            logger.level = LogService.INFO
            logger.level_is_overridden = False

    def rewrite_json(self):
        """Rewrite the log configuration file with the current level overrides.
        
        This method updates the log configuration file (_CONFIG) with the current state of the 
        level overrides (_level_overrides) in JSON format.
        """
        print("Will rewrite log config " + _CONFIG)
        with open(_CONFIG, "w", encoding="utf-8") as json_file:
            json.dump(self._level_overrides, json_file)

    def get_or_create_log_channel(self, name):
        """Get an existing log channel or create a new one if it doesn't exist.
        
        This method checks if a log channel with the specified name exists. If it does not, 
        it creates a new log channel with the default log level. If there is a level override 
        for the specified name, it sets the log level to the overridden value.
        
        Args:
            name (str): The name of the log channel.
        
        Returns:
            Logger: The log channel with the specified name.
        """
        if name not in self._loggers:
            self._loggers[name] = Logger(name, self._default_log_level)
            if name in self._level_overrides:
                self._loggers[name].set_level(self._level_overrides[name])
        return self._loggers[name]

    def set_default_log_level(self, level):
        """Set the default log level for all log channels.
        
        This method updates the default log level and applies it to all existing log channels 
        that do not have an overridden log level. It also updates the log configuration file 
        with the new default log level.
        
        Args:
            level (int): The log level to set as the default.
        """
        self._default_log_level = level
        self._level_overrides["default"] = level
        for logger in self._loggers.values():
            if not logger.level_is_overridden:
                logger.level = level
        self.rewrite_json()

    def set_level_override(self, logger_name, level):
        """Set a specific log level for a given log channel, overriding the default level.
        
        This method sets a custom log level for the specified log channel and updates the 
        log configuration file with the new level override.
        
        Args:
            logger_name (str): The name of the log channel.
            level (int): The log level to set for the specified log channel.
        """
        logger = self.get_or_create_log_channel(logger_name)
        self._level_overrides[logger_name] = level
        logger.set_level(level)
        self.rewrite_json()

    def get_loggers_list_as_property_enum(self, log_filter=""):
        """Return a list of loggers in a format suitable for UI property enums.
        
        This method generates a list of loggers, which can be used to select loggers 
        in the UI. Each logger is represented as a tuple containing the logger name 
        and a description. The list can be filtered by a prefix.
        
        Args:
            log_filter (str): A prefix to filter the loggers by name. If "ALL" is provided, no filtering is applied.
        
        Returns:
            list: A list of tuples representing loggers for UI property enums.
        """
        if log_filter == "ALL":
            log_filter = ""
        loggers = [("default", "default", "the default log level", 0)]
        current = 1
        logger_names = list(self._loggers.keys())
        logger_names.sort()
        for name in logger_names:
            if not log_filter or name.startswith(log_filter):
                loggers.append((name, name, name, current))
                current = current + 1
        return loggers

    def get_loggers_categories_as_property_enum(self):
        """Return a list of logger categories in a format suitable for UI property enums.
        
        This method generates a list of logger categories, which can be used to filter loggers 
        in the UI. Each category is represented as a tuple containing the category name and 
        a description. The list includes an option to show all loggers without filtering.
        
        Returns:
            list: A list of tuples representing logger categories for UI property enums.
        """
        categories = [("ALL", "(no filter)", "Do not filter: show all loggers", 0)]
        current = 1
        logger_names = list(self._loggers.keys())
        logger_names.sort()
        category_names = []
        for name in logger_names:
            if not "." in name:
                cat = name
            else:
                (cat, suffix) = str(name).split(".", 1)
            if not cat in category_names:
                category_names.append(cat)
                categories.append((cat, cat, cat, current))
                current = current + 1
        return categories

    def get_loggers(self):
        """Return the dictionary of currently defined loggers.
        
        This method provides access to the internal dictionary that holds all the loggers 
        created by the LogService. The dictionary keys are the logger names, and the values 
        are the Logger instances.
        
        Returns:
            dict: A dictionary of logger names and their corresponding Logger instances.
        """
        return self._loggers


_LOGSERVICE = _LogService()
