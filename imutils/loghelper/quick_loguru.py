# Simple loguru configurator
from loguru import logger
from loguru._logger import Core as _Core
from loguru._logger import Logger as _Logger
from multiprocessing import SimpleQueue
from multiprocessing.queues import SimpleQueue as SimpleQueueClass
import threading
from typing import Union
from pathlib import Path
import sys

class FilterLogger(_Logger):
    """Filter logger class for loguru logger.
    This class is a wrapper for loguru logger. It can filter the log messages bevor sending them to the logger.
    The filter is based on the log level and the debug mode and adds a identifier called classname.
    verbose is equal to the log level names and int values, debug is a boolean that blocks debug and trace methods.
    Args:
        classname (str, optional): Identifier. Defaults to None (FilterLogger).
        verbose (Union[int,str], optional): log level. Defaults to 'INFO'.
        debug (bool, optional): filter debug and trace. Defaults to False.
    """
    def __init__(self, classname: str = None, verbose: Union[int,str] = 'INFO', debug: bool = False):
        super().__init__(core=_Core(), exception=None, depth=0, record=False, lazy=False, colors=False, raw=False, capture=True, patchers=[], extra={},)
        self.debug_bool: bool = None
        self.verbose: int = None
        if verbose is None: verbose = 'INFO'
        if debug is None: debug = False
        self.log_levels: dict = {"TRACE": 5, "DEBUG": 10, "INFO": 20,
                                 "SUCCESS": 25, "WARNING": 30, "ERROR": 40,
                                 "CRITICAL": 50}
        self.set_filter_level(verbose, debug)
        if classname is None:
            self._logger = logger.bind(classname=self.__class__.__name__)
        else:
            self._logger = logger.bind(classname=classname)
    
    def set_classname(self, classname: str):
        self._logger = logger.bind(classname=classname)
    
    def set_filter_level(self, verbose: Union[int,str] = None, debug: bool = None):
        if not debug is None:
            self.debug_bool = debug
        if not verbose is None:
            if type(verbose) == str:
                try:
                    self.verbose = self.log_levels[verbose]
                except KeyError:
                    self.verbose = self.log_levels["INFO"]
            else:
                self.verbose = verbose
    
    def trace(self, message: str):
        if self.debug_bool and self.verbose <= 5:
            self._logger.trace(message)
    
    def debug(self, message: str):
        if self.debug_bool and self.verbose <=10:
            self._logger.debug(message)
    
    def info(self, message: str):
        if self.verbose <= 20:
            self._logger.info(message)
    
    def success(self, message: str):
        if self.verbose <= 25:
            self._logger.success(message)
    
    def warning(self, message: str):
        if self.verbose <= 30:
            self._logger.warning(message)
    
    def error(self, message: str):
        if self.verbose <= 40:
            self._logger.error(message)
            
    def critical(self, message: str):
        if self.verbose <= 50:
            self._logger.critical(message)
            
    def log(self, level: str, message: str):
        try:
            level_int = self.log_levels[level]
        except KeyError:
            self._logger.warning(f"Log level {level} not found. Using 0 instead.")
            level_int = 0
        if self.verbose <= level_int:
            self._logger.log(level, message)

 
class LoguruConfigurator:
    """Just to help to configure loguru logger with some default settings.
    Multiprocessing handler: If you want to use loguru in multiprocessing environment,
    you can use the multiprocessing handler as main sink collecting the logs.
    The client can be configured with the multiprocessing queue to send the logs to the handler.
    Pass the .get_client_queue of __main__ to the LoguruConfigurator of the client. 
    Args:
        log_level (str, optional): Log level. Defaults to "INFO".
        console_output (bool, optional): Activate or deactivate the console output. Defaults to True.
        console_error_output (bool, optional): Activate or deactivate the console error output. Defaults to False.
        file_ouput (bool, optional): Activate or deactivate the file output. Defaults to False.
        log_file (Union[Path,str], optional): Path to the log file. Defaults to None.
        run_multiprocessing_handler (bool, optional): Run the multiprocessing handler. Defaults to False.
        configure_multiprocessing_client_queue (SimpleQueue, optional): Configure the multiprocessing client queue. Defaults to None.
        verbose (Union[int, str], optional): Verbose level of this class. Defaults to 'TRACE'.
        debug (bool, optional): Activate or deactivate the debug mode of this class. Defaults to False.
        """
    def __init__(self, log_level: str = "INFO", console_output: bool = True, console_error_output: bool = False,
                 file_ouput: bool = False, log_file: Union[Path,str] = None, run_multiprocessing_handler: bool = False,
                 configure_multiprocessing_client_queue: SimpleQueue = None, verbose: Union[int, str] = 'TRACE',
                 debug: bool = False):
        
        self.debug_bool: bool = debug
        self.verbose: Union[int, str] = verbose
        self.log_level: str = log_level
        self._console_output: bool = console_output
        self._console_error_output = console_error_output
        self._console_sink_id: int = None
        self._console_sink_error_id: int = None
        self._console_log_error_output: bool = False
        self.log_levels: dict = {"TRACE": 5, "DEBUG": 10, "INFO": 20, "SUCCESS": 25, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        self._logger_sink_dict: dict = {}
        self.console_logger_format_debug = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSSS!UTC}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level> | "
            "<cyan>M_{module}</cyan>:<cyan>N_{name}</cyan>:class_<cyan>{extra[classname]}</cyan>:<cyan>func_{function}</cyan>:<cyan>line_{line}</cyan> | "
            "<m>t_{elapsed}</m>:<m>p_{process}</m>:<m>th_{thread}</m>:<m>ex_{exception}</m>")
        self.console_logger_format_std = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSSS!UTC}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[classname]}</cyan> | "
            "<level>{message}</level>")
        self.file_logger_format_std = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSSS!UTC}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[classname]}</cyan> | "
            "<level>{message}</level>")
        logger.configure(extra={"classname": "Unknown"})
        self.logger = FilterLogger(classname=self.__class__.__name__, debug=debug, verbose=verbose)

        self._run_multiprocessing_handler_bool: bool = run_multiprocessing_handler
        self.logger.debug(f"run_multiprocessing_handler: {self._run_multiprocessing_handler_bool}")
        self._configure_multiprocessing_client_bool: bool = configure_multiprocessing_client_queue is not None
        self.logger.debug(f"configure_multiprocessing_client: {self._configure_multiprocessing_client_bool}")

        if not self._configure_multiprocessing_client_bool:
            logger.remove()
            self.set_console_logger(log_level, active = self._console_output)
            self.set_console_error_logger(active = self._console_error_output)
            self._file_log_level = log_level
            self._file_sink_id = None
            self._file_output = False
            self._json_file_log_level = log_level
            self._json_file_sink_id = None
            self._json_file_output = False
            self.set_file_logger(log_level, log_file, file_ouput)
            self.logger.info("Loguru configurator initialized.")

        # Needed for unified logging in multiprocessing
        self._queue: SimpleQueueClass = SimpleQueue()
        self._handler_process_running: threading.Event = threading.Event()
        self._handler_process_running.clear()
        self._handler_process: threading.Thread = None
        if self._run_multiprocessing_handler_bool and not self._configure_multiprocessing_client_bool:
            self._run_multiprocessing_handler()
        elif self._configure_multiprocessing_client_bool and not self._run_multiprocessing_handler_bool:
            self._configure_multiprocessing_client(configure_multiprocessing_client_queue)
        elif self._run_multiprocessing_handler_bool and self._configure_multiprocessing_client_bool:
            self.logger.error("Both run_multiprocessing_handler and configure_multiprocessing_client are True. you can't be handler and client at the same time.")
            ValueError("Both run_multiprocessing_handler and configure_multiprocessing_client are True. you can't be handler and client at the same time.")
            # you can be ether client or handler, not both

    def __del__(self):
        self.logger.info("deallocating LoguruConfigurator.")
        self._stop_multiprocessing_handler()

    def set_log_level(self, verbose: Union[int,str] = 'INFO', debug: bool = False):
        """Set the log level for internal class debugging."""
        self.debug_bool: bool = debug
        self.verbose: str = verbose
        self.logger.set_filter_level(verbose, debug)

    def get_filter_logger(self, classname: str, verbose: Union[int,str] = None, debug: bool = None):
        """Get a filter logger.
        Args:
            classname (str): Log message identifier.
            verbose (Union[int,str], optional): log level. Defaults to None (takes configurator state).
            debug (bool, optional): filter debug and trace. Defaults to None (takes configurator state)."""
        if verbose is None:
            verbose = self.verbose
        if debug is None:
            debug = self.debug_bool
        """Get a logger with class name."""
        return FilterLogger(classname=classname, verbose=verbose, debug=debug)

    def _formatter(self, record):
        """Custom formatter for loguru logger."""
        if record["level"].no > logger.level("WARNING").no:
            return self.console_logger_format_debug + "\n"
        keyname = "{name}" if record["extra"]["classname"] == "Unknown" else "{extra[classname]}"
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSSS!UTC}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>%s</cyan> | " 
            "<level>{message}</level>\n" % keyname)
    
    def set_console_error_logger(self, active: bool = True):
        """Set the stderr logger for error messages.
        
        Args:
            active (bool, optional): Activate or deactivate the error logger. Defaults to True.
        """
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("set_console_error_logger is not available in multiprocessing client mode.")
            return
        self._console_log_error_output = active
        if self._console_sink_error_id is not None:
            #logger.remove(self._console_sink_error_id)
            self.remove_logger_sink(self._console_sink_error_id)
            self._console_sink_error_id = None
        if active:
            self._console_sink_error_id = self.add_logger_sink(sys.stderr, log_level="ERROR", format=self.console_logger_format_debug, colorize=True)
            #self._console_sink_error_id = logger.add(sys.stderr, colorize=True, format=self.console_logger_format_debug, log_level="ERROR", enqueue=True)
    
    def set_console_logger(self, log_level: str, active: bool = True, detailed_error: bool = False, details: bool = False):
        """Set the console logger.
        Args:
            log_level (str): Log level for the console logger.
            active (bool, optional): Activate or deactivate the console logger. Defaults to True.
        """
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("set_console_logger is not available in multiprocessing client mode.")
            return
        self._console_log_level = log_level
        self._console_log_output = active
        if self._console_sink_id is not None:
            self.remove_logger_sink(self._console_sink_id)
            self._console_sink_id = None
            #logger.remove(self._console_sink_id)
        if active:
            if log_level == "DEBUG" or log_level == "TRACE":
                self._console_sink_id = self.add_logger_sink(sys.stdout, log_level=log_level, format=self.console_logger_format_debug, colorize=True)
                #self._console_sink_id = logger.add(sys.stdout, colorize=True, format=self.console_logger_format_debug, log_level=log_level, enqueue=True)
            else:
                format = self.console_logger_format_std if not detailed_error else self._formatter
                format = self.console_logger_format_debug if details else format
                self._console_sink_id = self.add_logger_sink(sys.stdout, log_level=log_level, format=format, colorize=True)
                #self._console_sink_id = logger.add(sys.stdout, colorize=True, format=format, log_level=log_level, enqueue=True)
    
    def set_json_file_logger(self, log_level: str, file: Union[Path,str], active: bool = True):
        """Set the json file logger.
        Args:
            log_level (str): Log level for the json file logger.
            file (Union[Path,str]): Path to the json file.
            active (bool, optional): Activate or deactivate the json file logger. Defaults to True."""
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("set_json_file_logger is not available in multiprocessing client mode.")
            return
        self._json_file_log_level = log_level
        self._json_file_output = active
        if self._json_file_sink_id is not None:
            self.remove_logger_sink(self._json_file_sink_id)
            self._json_file_sink_id = None
            #logger.remove(self._json_file_sink_id)
        if active:
            self._json_file_sink_id = self.add_logger_sink(file, log_level=log_level, format="file logger", serialize=True)
            #self._json_file_sink_id = logger.add(file, format="file logger", log_level=log_level, serialize=True, enqueue=True)
            
    def set_file_logger(self, log_level: str, file: Union[Path,str], active: bool = True):
        """Set the file logger.
        Args:
            log_level (str): Log level for the file logger.
            file (Union[Path,str]): Path to the file.
            active (bool, optional): Activate or deactivate the file logger. Defaults to True.
        """
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("set_file_logger is not available in multiprocessing client mode.")
            return
        self._file_log_level = log_level
        self._file_output = active
        if self._file_sink_id is not None:
            self.remove_logger_sink(self._file_sink_id)
            self._file_sink_id = None
            #logger.remove(self._file_sink_id)
        if active:
            if log_level == "DEBUG" or log_level == "TRACE":
                self._file_sink_id = self.add_logger_sink(file, log_level=log_level, format=self.console_logger_format_debug)
                #self._file_sink_id = logger.add(file, format=self.console_logger_format_debug, log_level=log_level, enqueue=True)
            else:
                self._file_sink_id = self.add_logger_sink(file, log_level=log_level, format=self.file_logger_format_std)
                #self._file_sink_id = logger.add(file, format=self.file_logger_format_std, log_level=log_level, enqueue=True)

    def add_logger_sink(self, sink, log_level: str, format: str, filter=None, colorize=None, serialize=False, backtrace=True, diagnose=True, context=None, catch=True, **kwargs):
        """Add a new logger.
        Args:
            sink: Sink for the logger.
            log_level (str): Log level for the logger.
            format (str): Format for the logger.
        """
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("add_logger_sink is not available in multiprocessing client mode.")
            return
        logger_id = logger.add(sink, format=format, level=log_level, filter=filter, colorize=colorize, serialize=serialize, backtrace=backtrace, diagnose=diagnose, enqueue=True, context=context, catch=catch, **kwargs)
        for key, value in self._logger_sink_dict.items():
            if value['sink'] == sink:
                self.logger.warning(f"Sink {sink} already in use and dublicated.")
        self._logger_sink_dict[logger_id] = {'sink': sink, 'level': log_level, 'format': format, 'filter': filter, 'colorize': colorize, 'serialize': serialize,
                                             'backtrace': backtrace, 'diagnose': diagnose, 'enqueue': True, 'context': context, 'catch': catch}
        self.logger.info(f"Added sink id {logger_id}, sink: {sink}, level: {log_level}")
        return logger_id
    
    def get_logger_sinks(self):
        """Get the loggers."""
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("get_logger_sink is not available in multiprocessing client mode.")
            return
        return self._logger_sink_dict
    
    def remove_logger_sink(self, sink_id):
        """Remove a logger.
        Args:
            sink_id: Id of the logger.
        """
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("remove_logger_sink is not available in multiprocessing client mode.")
            return
        if sink_id in self._logger_sink_dict:

            self.logger.info(f"Removing sink id {sink_id}, sink: {self._logger_sink_dict[sink_id]['sink']}, level: {self._logger_sink_dict[sink_id]['level']}")
            logger.remove(sink_id)
            del self._logger_sink_dict[sink_id]
        else:
            self.logger.error(f"Sink id {sink_id} not found.")

    def write_log(self, log_level: str = "INFO", message: str = "NOTHING TO LOG"):
        """Write a log message.
        Args:
            message (str): Log message.
            log_level (str, optional): Log level. Defaults to "INFO".
        """
        self.logger.log(log_level, message)

    def filter_by_classname(self, classname: str):
        """Filter the log messages by class name."""
        return lambda record: record["extra"].get("classname") == classname
    
    def reinitialize_logger(self):
        """Reinitialize the logger."""
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("reinitialize_logger is not available in multiprocessing client mode.")
            return
        self.logger.info("Reinitializing logger configuration.")
        logger.remove()
        old_logger_sink_dict = self._logger_sink_dict
        self._logger_sink_dict = {}
        for key, value in old_logger_sink_dict.items():
            self.add_logger_sink(value['sink'], value['level'], value['format'], value['filter'], value['colorize'], value['serialize'], value['backtrace'], value['diagnose'], value['context'], value['catch'])
        self.logger.info("Logger reinitialized.")

    def _run_multiprocessing_handler(self):
        """Run the multiprocessing handler."""
        self._handler_process = threading.Thread(target=self._handler_process_target, daemon=True)
        self._handler_process.start()
        self.logger.info("Multiprocessing handler started.")

    def _handler_process_target(self):
        """Handler process target."""
        self.logger.info("Starting handler process.")
        self._handler_process_running.set()
        while self._handler_process_running.is_set():
            try:
                record = self._queue.get()
                if record == "CLOSE":
                    self.logger.info("Handler process received close signal.")
                    break
                level, message, classname = record["level"].name, record["message"], record["extra"]["classname"]
                self.logger.debug(f"Handler process received record: {record}")
                logger.bind(classname=classname).patch(lambda record: record.update(record)).log(level, message)
            except Exception as e:
                self.logger.error(f"Error in handler process: {e}")
    
    def _stop_multiprocessing_handler(self):
        """Stop the multiprocessing handler."""
        self._handler_process_running.clear()
        if self._handler_process is not None:
            self._queue.put("CLOSE")
            self._handler_process.join()
        self.logger.info("Multiprocessing handler stopped.")

    def _configure_multiprocessing_client(self, queue: SimpleQueue):
        """Configure the multiprocessing client."""
        # remove all sinks
        logger.remove()
        self._queue = queue
        logger.configure(handlers=[{"sink": self}], extra={"classname": "Unknown"})
        self.logger.info("Multiprocessing client configured.")

    def get_client_queue(self) -> SimpleQueue:
        """Get the client queue."""
        if self._configure_multiprocessing_client_bool:
            self.logger.warning("get_client_queue is not available in multiprocessing client mode.")
            return
        return self._queue

    def write(self, message):
        """Write a message as sink."""
        self._queue.put(message.record)

