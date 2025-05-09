import pandas as pd
from tabulate import tabulate

def style_metadata(func):
    def wrapper(self, value):
        result = func(self, value)
        formatted_result = (
            tabulate(result, headers='keys', tablefmt='pretty', showindex=False)
            if isinstance(result, pd.DataFrame) 
            else result
        )
        return f"=== start ===\n{formatted_result}\n=== end ==="
    return wrapper
