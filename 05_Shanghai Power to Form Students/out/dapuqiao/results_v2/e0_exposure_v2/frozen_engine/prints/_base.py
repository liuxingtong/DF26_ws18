"""prints 共用底座 —— notebook 里学生看到的文字都从这里出。
=================================================================
_say  = 薄薄一层 print(不加前缀):每个 prints.* 只管「说什么」,不管「怎么印」。
        将来要加前缀 / 落盘 / 静音,只改这一处。
ready = setup 格最后一行的就绪回报:确认引擎已载入、现在跑哪个站点。
"""
import config


def _say(*args):
    """所有回报统一走这里(等同 print,单一出口好维护)。"""
    print(*args)


def ready():
    """setup 格跑完的就绪回报:引擎已载入,当前站点是谁(改 config.SLUG 换站)。"""
    _say("引擎就绪 · 当前站点:%s(%s)" % (config.site_name(), config.SLUG))
