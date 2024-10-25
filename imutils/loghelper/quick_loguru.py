# Simple loguru configurator
from loguru import logger
from typing import Union
from pathlib import Path
import sys

class LoguruConfigurator:
    """Just to help to configure loguru logger with some default settings.
       Pass the logger to processes and add <process_logger>.complete() on the end of the process."""
    def __init__(self, log_level: str = "INFO", consol_output: bool = True, file_ouput: bool = False, log_file: Union[Path,str] = None):
        self._consol_log_level = log_level
        self._consol_output = consol_output
        self._consol_sink_id = None
        self._consol_sink_error_id = None
        self._consol_log_error_output = False
        self._consol_logger_format_debug = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSSS!UTC}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level> | "
            "<cyan>M_{module}</cyan>:<cyan>N_{name}</cyan>:class_<cyan>{extra[classname]}</cyan>:<cyan>func_{function}</cyan>:<cyan>line_{line}</cyan> | "
            "<m>t_{elapsed}</m>:<m>p_{process}</m>:<m>th_{thread}</m>:<m>ex_{exception}</m>")
        self._consol_logger_format_std = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSSS!UTC}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[classname]}</cyan> | "
            "<level>{message}</level>")
        self._file_logger_format_std = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSSS!UTC}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[classname]}</cyan> | "
            "<level>{message}</level>")
        logger.configure(extra={"classname": "Unknown"})
        logger.remove()
        self.set_consol_logger(log_level)
        self.set_consol_error_logger()
        self._file_log_level = log_level
        self._file_sink_id = None
        self._file_output = False
        self._json_file_log_level = log_level
        self._json_file_sink_id = None
        self._json_file_output = False
        self.set_file_logger(log_level, log_file, file_ouput)
    
    def formatter(self, record):
        """Custom formatter for loguru logger."""
        if record["level"].no > logger.level("WARNING").no:
            return self._consol_logger_format_debug + "\n"
        keyname = "{name}" if record["extra"]["classname"] == "Unknown" else "{extra[classname]}"
        return (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSSS!UTC}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>%s</cyan> | " 
            "<level>{message}</level>\n" % keyname)
    
    def set_consol_error_logger(self, active: bool = True):
        """Set the stderr logger for error messages.
        
        Args:
            active (bool, optional): Activate or deactivate the error logger. Defaults to True.
        """
        self._consol_log_error_output = active
        if self._consol_sink_error_id is not None:
            logger.remove(self._consol_sink_error_id)
        if active:
            self._consol_sink_error_id = logger.add(sys.stderr, colorize=True, format=self._consol_logger_format_debug, level="ERROR", enqueue=True)
    
    def set_consol_logger(self, log_level: str, active: bool = True, detailed_error: bool = True):
        """Set the console logger.
        
        Args:
            log_level (str): Log level for the console logger.
            active (bool, optional): Activate or deactivate the console logger. Defaults to True.
        """
        self._consol_log_level = log_level
        self._consol_log_output = active
        if self._consol_sink_id is not None:
            logger.remove(self._consol_sink_id)
        if active:
            if log_level == "DEBUG" or log_level == "TRACE":
                self._consol_sink_id = logger.add(sys.stdout, colorize=True, format=self._consol_logger_format_debug, level=log_level, enqueue=True)
            else:
                format = self._consol_logger_format_std if not detailed_error else self.formatter
                self._consol_sink_id = logger.add(sys.stdout, colorize=True, format=format, level=log_level, enqueue=True)
    
    def set_json_file_logger(self, log_level: str, file: Union[Path,str], active: bool = True):
        """Set the json file logger.
        
        Args:
            log_level (str): Log level for the json file logger.
            file (Union[Path,str]): Path to the json file.
            active (bool, optional): Activate or deactivate the json file logger. Defaults to True."""
        self._json_file_log_level = log_level
        self._json_file_output = active
        if self._json_file_sink_id is not None:
            logger.remove(self._json_file_sink_id)
        if active:
            self._json_file_sink_id = logger.add(file, format="file logger", level=log_level, serialize=True, enqueue=True)
            
    def set_file_logger(self, log_level: str, file: Union[Path,str], active: bool = True):
        """Set the file logger.
        
        Args:
            log_level (str): Log level for the file logger.
            file (Union[Path,str]): Path to the file.
            active (bool, optional): Activate or deactivate the file logger. Defaults to True.
        """
        self._file_log_level = log_level
        self._file_output = active
        if self._file_sink_id is not None:
            logger.remove(self._file_sink_id)
        if active:
            if log_level == "DEBUG" or log_level == "TRACE":
                self._file_sink_id = logger.add(file, format=self._consol_logger_format_debug, level=log_level, enqueue=True)
            else:
                self._file_sink_id = logger.add(file, format=self._file_logger_format_std, level=log_level, enqueue=True)
