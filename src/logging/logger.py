import logging
import os
from datetime import datetime

class DynamicLogger:
    def __init__(self, log_dir=None):
        """
        :param log_dir: Optional fixed path to save log files. 
                        Defaults to project root / 'logs' folder.
        """
        self.current_logger = None
        self.current_log_file = None
        if log_dir is None:
            # Default log directory is a 'logs' folder in the root of the project
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.log_dir = os.path.join(project_root, "logs")
        else:
            self.log_dir = log_dir
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
    
    def _setup_new_logger(self):
        """Create a new logger with a fresh timestamp"""
        
        log_filename = f"{datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}.log"
        log_file_path = os.path.join(self.log_dir, log_filename)
        
        
        logger_name = f"training_logger_{log_filename}"
        new_logger = logging.getLogger(logger_name)
        new_logger.setLevel(logging.INFO)
        
        # Remove any existing handlers
        for handler in new_logger.handlers[:]:
            new_logger.removeHandler(handler)
        
        
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.INFO)
        
        
        formatter = logging.Formatter("[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        
        new_logger.addHandler(file_handler)
        
        self.current_logger = new_logger
        self.current_log_file = log_file_path
        return new_logger
    
    def info(self, message):
        if self.current_logger is None:
            self._setup_new_logger()
        self.current_logger.info(message)
    
    def error(self, message):
        if self.current_logger is None:
            self._setup_new_logger()
        self.current_logger.error(message)
    
    def warning(self, message):
        if self.current_logger is None:
            self._setup_new_logger()
        self.current_logger.warning(message)
    
    def debug(self, message):
        if self.current_logger is None:
            self._setup_new_logger()
        self.current_logger.debug(message)
    
    def get_new_logger(self):
        
        self.current_logger = None
        self.current_log_file = None
        return self._setup_new_logger()


logger = DynamicLogger()
