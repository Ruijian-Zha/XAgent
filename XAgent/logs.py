"""Logging module for Auto-GPT."""
import logging
import os
import random
import re
import time
import json
import abc
from logging import LogRecord
from typing import Any
import uuid
from threading import Lock

from colorama import Fore, Style

from XAgent.utils import Singleton, TaskSaveItem

class JsonFileHandler(logging.FileHandler):
    def __init__(self, filename, mode="a", encoding=None, delay=False):
        super().__init__(filename, mode, encoding, delay)

    def emit(self, record):
        json_data = json.loads(self.format(record))
        with open(self.baseFilename, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return record.msg


class Logger(metaclass=Singleton):
    """
    Logger that handle titles in different colors.
    Outputs logs in console, activity.log, and errors.log
    For console handler: simulates typing
    """

    def __init__(self):
        # create log directory if it doesn't exist
        this_files_dir_path = os.path.dirname(__file__)
        log_dir = os.path.join(this_files_dir_path, "../logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = "activity.log"
        error_file = "error.log"

        console_formatter = RecordFormatter("%(title_color)s %(message)s")

        # Create a handler for console which simulate typing
        self.typing_console_handler = TypingConsoleHandler()
        self.typing_console_handler.setLevel(logging.INFO)
        self.typing_console_handler.setFormatter(console_formatter)

        # Create a handler for console without typing simulation
        self.console_handler = ConsoleHandler()
        self.console_handler.setLevel(logging.DEBUG)
        self.console_handler.setFormatter(console_formatter)

        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        # Info handler in activity.log
        self.file_handler = logging.FileHandler(
            os.path.join(log_dir, log_file), "a", "utf-8"
        )
        self.file_handler.setLevel(logging.DEBUG)
        info_formatter = RecordFormatter(
            "%(asctime)s %(levelname)s %(title)s %(message_no_color)s"
        )
        self.file_handler.setFormatter(info_formatter)

        # Error handler error.log
        error_handler = logging.FileHandler(
            os.path.join(log_dir, error_file), "a", "utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = RecordFormatter(
            "%(asctime)s %(levelname)s %(module)s:%(funcName)s:%(lineno)d %(title)s"
            " %(message_no_color)s"
        )
        error_handler.setFormatter(error_formatter)

        self.typing_logger = logging.getLogger("TYPER")
        self.typing_logger.addHandler(self.typing_console_handler)
        self.typing_logger.addHandler(self.file_handler)
        self.typing_logger.addHandler(error_handler)
        self.typing_logger.setLevel(logging.DEBUG)

        self.logger = logging.getLogger("LOGGER")
        self.logger.addHandler(self.console_handler)
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(error_handler)
        self.logger.setLevel(logging.DEBUG)

        self.json_logger = logging.getLogger("JSON_LOGGER")
        self.json_logger.addHandler(self.file_handler)
        self.json_logger.addHandler(error_handler)
        self.json_logger.setLevel(logging.DEBUG)

        self.speak_mode = False
        self.chat_plugins = []
        self.log_lock = Lock()


    def typewriter_log(
        self, title="", title_color="", content="", speak_text=False, level=logging.INFO
    ):
        # if speak_text and self.speak_mode:
        #     say_text(f"{title}. {content}")
        for plugin in self.chat_plugins:
            plugin.report(f"{title}. {content}")

        if content:
            if isinstance(content, list):
                content = " ".join(content)
        else:
            content = ""
        self.log_lock.acquire()
        self.typing_logger.log(
            level, content, extra={"title": title, "color": title_color}
        )
        self.log_lock.release()

    def debug(
        self,
        message,
        title="",
        title_color="",
    ):
        self._log(title, title_color, message, logging.DEBUG)

    def info(
        self,
        message,
        title="",
        title_color="",
    ):
        self._log(title, title_color, message, logging.INFO)

    def warn(
        self,
        message,
        title="",
        title_color="",
    ):
        self._log(title, title_color, message, logging.WARN)

    def error(self, title, message=""):
        self._log(title, Fore.RED, message, logging.ERROR)

    def _log(
        self,
        title: str = "",
        title_color: str = "",
        message: str = "",
        level=logging.INFO,
    ):
        if message:
            if isinstance(message, list):
                message = " ".join(message)
        self.logger.log(
            level, message, extra={"title": str(title), "color": str(title_color)}
        )

    def set_level(self, level):
        self.logger.setLevel(level)
        self.typing_logger.setLevel(level)

    def double_check(self, additionalText=None):
        if not additionalText:
            additionalText = (
                "Please ensure you've setup and configured everything"
                " correctly. Read https://github.com/Torantulino/Auto-GPT#readme to "
                "double check. You can also create a github issue or join the discord"
                " and ask there!"
            )

        self.typewriter_log("DOUBLE CHECK CONFIGURATION", Fore.YELLOW, additionalText)

    def log_json(self, data: Any, file_name: str) -> None:
        # Define log directory
        this_files_dir_path = os.path.dirname(__file__)
        log_dir = os.path.join(this_files_dir_path, "../logs")

        # Create a handler for JSON files
        json_file_path = os.path.join(log_dir, file_name)
        json_data_handler = JsonFileHandler(json_file_path)
        json_data_handler.setFormatter(JsonFormatter())

        # Log the JSON data using the custom file handler
        self.json_logger.addHandler(json_data_handler)
        self.json_logger.debug(data)
        self.json_logger.removeHandler(json_data_handler)

    def get_log_directory(self):
        this_files_dir_path = os.path.dirname(__file__)
        log_dir = os.path.join(this_files_dir_path, "../logs")
        return os.path.abspath(log_dir)


"""
Output stream to console using simulated typing
"""


class TypingConsoleHandler(logging.StreamHandler):
    def emit(self, record):
        min_typing_speed = 0.05
        max_typing_speed = 0.01

        msg = self.format(record)
        try:
            words = msg.split()
            for i, word in enumerate(words):
                print(word, end="", flush=True)
                if i < len(words) - 1:
                    print(" ", end="", flush=True)
                typing_speed = random.uniform(min_typing_speed, max_typing_speed)
                time.sleep(typing_speed)
                # type faster after each word
                min_typing_speed = min_typing_speed * 0.95
                max_typing_speed = max_typing_speed * 0.95
            print()
        except Exception:
            self.handleError(record)


class ConsoleHandler(logging.StreamHandler):
    def emit(self, record) -> None:
        msg = self.format(record)
        try:
            print(msg)
        except Exception:
            self.handleError(record)


class RecordFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        if hasattr(record, "color"):
            record.title_color = (
                getattr(record, "color")
                + getattr(record, "title", "")
                + " "
                + Style.RESET_ALL
            )
        else:
            record.title_color = getattr(record, "title", "")

        # Add this line to set 'title' to an empty string if it doesn't exist
        record.title = getattr(record, "title", "")

        if hasattr(record, "msg"):
            record.message_no_color = remove_color_codes(getattr(record, "msg"))
        else:
            record.message_no_color = ""
        return super().format(record)


def remove_color_codes(s: str) -> str:
    if not isinstance(s,str):
        s = json.dumps(s)
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", s)


logger = Logger()


def print_task_save_items(
    item: TaskSaveItem,
) -> None:

    logger.typewriter_log(
        f"Task Name:", Fore.YELLOW, f"{item.name}"
    )
    logger.typewriter_log(
        f"Task Goal:", Fore.YELLOW, f"{item.goal}"
    )
    logger.typewriter_log(
        f"Task Prior-Criticism:", Fore.YELLOW, f"{item.prior_plan_criticism}"
    )
    if len(item.posterior_plan_reflection) > 0:
        logger.typewriter_log(
            f"Task Posterior-Criticism:", Fore.YELLOW
        )
        for line in item.posterior_plan_reflection:
            line = line.lstrip("- ")
            logger.typewriter_log("- ", Fore.GREEN, line.strip())
    if len(item.milestones) > 0:
        logger.typewriter_log(
            f"Task Milestones:", Fore.YELLOW,
        )
        for line in item.milestones:
            line = line.lstrip("- ")
            logger.typewriter_log("- ", Fore.GREEN, line.strip())
    # if len(item.expected_tools) > 0:
    #     logger.typewriter_log(
    #         f"Expected Tools:", Fore.YELLOW,
    #     )
    #     for line in item.expected_tools:
    #         line = f"{line['tool_name']}: {line['reason']}".lstrip("- ")
    #         logger.typewriter_log("- ", Fore.GREEN, line.strip())
    if len(item.tool_reflection) > 0:
        logger.typewriter_log(
            f"Posterior Tool Reflections:", Fore.YELLOW,
        )
        for line in item.tool_reflection:
            line = f"{line['target_tool_name']}: {line['reflection']}".lstrip("- ")
            logger.typewriter_log("- ", Fore.GREEN, line.strip())

    logger.typewriter_log(
        f"Task Status:", Fore.YELLOW, f"{item.status.name}"
    )
    if item.action_list_summary != "":
        logger.typewriter_log(
            f"Action Summary:", Fore.YELLOW, f"{item.action_list_summary}"
        )

def print_assistant_thoughts(
    # ai_name: object,
    assistant_reply_json_valid: object,
    speak_mode: bool = False,
) -> None:
    assistant_thoughts_reasoning = None
    assistant_thoughts_plan = None
    assistant_thoughts_speak = None
    assistant_thoughts_criticism = None

    assistant_thoughts = assistant_reply_json_valid.get("thoughts", {})
    assistant_thoughts = assistant_thoughts.get("properties", {})
    assistant_thoughts_text = assistant_thoughts.get("thought")
    if assistant_thoughts:
        assistant_thoughts_reasoning = assistant_thoughts.get("reasoning")
        assistant_thoughts_plan = assistant_thoughts.get("plan")
        assistant_thoughts_criticism = assistant_thoughts.get("criticism")
    if assistant_thoughts_text is not None and assistant_thoughts_text != "":
        logger.typewriter_log(
            f"THOUGHTS:", Fore.YELLOW, f"{assistant_thoughts_text}"
        )
    if assistant_thoughts_reasoning is not None and assistant_thoughts_reasoning != "":
        logger.typewriter_log("REASONING:", Fore.YELLOW, f"{assistant_thoughts_reasoning}")
        
    if assistant_thoughts_plan is not None and len(assistant_thoughts_plan) > 0:
        logger.typewriter_log("PLAN:", Fore.YELLOW, "")
        # If it's a list, join it into a string
        if isinstance(assistant_thoughts_plan, list):
            assistant_thoughts_plan = "\n".join(assistant_thoughts_plan)
        elif isinstance(assistant_thoughts_plan, dict):
            assistant_thoughts_plan = str(assistant_thoughts_plan)

        # Split the input_string using the newline character and dashes
        lines = assistant_thoughts_plan.split("\n")
        for line in lines:
            line = line.lstrip("- ")
            logger.typewriter_log("- ", Fore.GREEN, line.strip())
            
    if assistant_thoughts_criticism is not None and assistant_thoughts_criticism != "":
        logger.typewriter_log("CRITICISM:", Fore.YELLOW, f"{assistant_thoughts_criticism}")
    return {
        "thoughts": assistant_thoughts_text,
        "reasoning": assistant_thoughts_reasoning,
        "plan": assistant_thoughts_plan,
        "criticism": assistant_thoughts_criticism,
        "node_id": uuid.uuid4().hex
    }
