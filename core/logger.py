from enum import Enum

class LogColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class LogType(Enum):
    WARNING = 0,
    INFO = 1,
    ERROR = 2

class Logger:

    is_debug = True

    @staticmethod
    def system(message: str):
        print(f"{LogColors.OKBLUE}System: {message}{LogColors.ENDC}")

    @staticmethod
    def warning(message: str):
        print(f"{LogColors.WARNING}Warning: {message}{LogColors.ENDC}")

    @staticmethod
    def error(message: str):
        print(f"{LogColors.FAIL}Error: {message}{LogColors.ENDC}")

    @staticmethod
    def info(message: str):
        print(f"{LogColors.OKCYAN}Info: {message}{LogColors.ENDC}")

    @staticmethod
    def log(message: str):
        print(f"{message}")

    @staticmethod
    def debug(message: str):
        if Logger.is_debug:
            print(f"{LogColors.OKGREEN}Debug: {message}{LogColors.ENDC}")

