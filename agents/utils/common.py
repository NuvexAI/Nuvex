import csv
import io
import time
from typing import List


def exists(val):
    return val is not None


def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def dict_to_csv(data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(data.keys())
    writer.writerow(data.values())

    return output.getvalue()


def concat_strings(string_list: List[str]) -> str:
    if not isinstance(string_list, list):
        raise TypeError("Input must be a list of strings.")

    if not all(isinstance(string, str) for string in string_list):
        raise TypeError("All elements in the list must be strings.")

    try:
        return "".join(string_list)
    except TypeError:
        raise TypeError("All elements in the list must be strings.")
