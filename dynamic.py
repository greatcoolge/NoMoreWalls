# dynamic.py
from typing import Callable, List, Union

# 定义函数类型
AUTOFUNTYPE = Callable[[], Union[str, List[str], Tuple[str], Set[str], None]]

# 返回空的列表
AUTOURLS: List[AUTOFUNTYPE] = []
AUTOFETCH: List[AUTOFUNTYPE] = []
