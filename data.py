# ============================================================
# data.py —— 数据获取模块
# ------------------------------------------------------------
# 职责（单一职责原则）：只负责「从网上把股票数据拿回来」，
# 并整理成统一格式的 DataFrame。不做任何因子计算、不碰界面。
#
# 为什么要单独拆一个文件？
#   - 以后换数据源（比如从 yfinance 换成别的），只改这里
#   - 因子计算、界面代码完全不受影响
#   - 这就是「关注点分离」，面试常考的工程思想
#
# 统一输出格式：所有函数都返回一个 pandas.DataFrame，
# 索引是日期，至少包含列：open, high, low, close, volume
# ============================================================

import time                  # 用于重试之间的等待
import pandas as pd          # 表格数据处理
import yfinance as yf        # 美股数据源


def _retry(func, times: int = 3, wait: float = 2.0):
    """
    通用重试工具：把一个「可能因网络抖动失败」的函数多试几次。

    参数：
        func:  一个不带参数的函数（用 lambda 包装要调用的逻辑）
        times: 最多尝试几次，默认 3 次
        wait:  每次失败后等待的秒数，默认 2 秒

    返回：
        func() 成功时的返回值。

    为什么需要它？
        网络请求偶尔会失败（连接被重置、限流等），
        很多时候「再试一次」就好了。这是处理网络的常见套路。
    """
    last_error = None
    for attempt in range(1, times + 1):
        try:
            return func()                 # 尝试执行
        except Exception as e:            # 失败就记下错误，等一会再试
            last_error = e
            print(f"第 {attempt} 次尝试失败：{e}")
            if attempt < times:
                time.sleep(wait)
    # 试满次数还失败，把最后一次的错误抛出去
    raise last_error


def get_us_stock(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    获取美股历史行情数据。

    参数：
        symbol: 股票代码，比如 "AAPL"（苹果）、"MSFT"（微软）
        period: 时间范围，比如 "1y"=一年, "6mo"=六个月, "5y"=五年

    返回：
        DataFrame，索引为日期，列为 open/high/low/close/volume

    说明：
        函数签名里的 `symbol: str` 是「类型注解」，
        告诉别人（和你自己）这个参数应该传字符串。
        Python 不强制，但写上可读性更好，也是专业习惯。
    """
    # yf.Ticker 创建一个「股票对象」，代表某只股票
    ticker = yf.Ticker(symbol)

    # .history() 下载历史数据，返回一个 DataFrame
    # 用 _retry 包一层：网络抖动/限流时自动重试 3 次
    df = _retry(lambda: ticker.history(period=period))

    # 如果代码写错或网络问题，可能返回空表，提前报错更好排查
    if df.empty:
        raise ValueError(f"没有获取到 {symbol} 的数据，请检查代码是否正确")

    # yfinance 返回的列名首字母大写（Open/High/Low/Close/Volume）
    # 我们统一改成小写，方便后续代码统一处理
    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })

    # 只保留我们关心的 5 列（其余如 Dividends 用不到）
    df = df[["open", "high", "low", "close", "volume"]]

    return df


def _to_sina_symbol(symbol: str) -> str:
    """
    把 6 位纯数字代码转成新浪财经需要的格式（带交易所前缀）。
        6 开头 -> 上交所 -> "sh600519"
        0/3 开头 -> 深交所 -> "sz000001"
        4/8 开头 -> 北交所 -> "bj430047"
    """
    if symbol.startswith("6"):
        return "sh" + symbol
    elif symbol.startswith(("0", "3")):
        return "sz" + symbol
    else:
        return "bj" + symbol


def get_cn_stock(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    获取 A 股历史行情数据（用 akshare）。

    参数：
        symbol: 6 位股票代码，比如 "600519"（贵州茅台）、"000001"（平安银行）
        period: 时间范围，同上（"1y"/"6mo"/"5y"）

    返回：
        与 get_us_stock 相同格式的 DataFrame。

    健壮性设计（重点）：
        采用「双数据源」——优先东方财富，失败自动切换到新浪财经。
        单一数据源不稳定时（限流、被封），另一个能兜底，
        这种「降级/容错」思路在真实工程里非常重要，面试也是加分点。
    """
    import akshare as ak      # 延迟导入：库大启动慢，用到才加载

    # 把 period 换算成天数，再算出开始日期
    period_to_days = {"6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
    days = period_to_days.get(period, 365)
    end_date = pd.Timestamp.today()
    start_date = end_date - pd.Timedelta(days=days)

    # ---------- 数据源 1：东方财富 ----------
    def fetch_eastmoney():
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="qfq",
        )
        # 东方财富是中文列名，统一改成英文
        df = df.rename(columns={
            "日期": "date", "开盘": "open", "最高": "high",
            "最低": "low", "收盘": "close", "成交量": "volume",
        })
        return df

    # ---------- 数据源 2：新浪财经（备用）----------
    def fetch_sina():
        df = ak.stock_zh_a_daily(
            symbol=_to_sina_symbol(symbol),
            start_date=start_date.strftime("%Y%m%d"),
            adjust="qfq",
        )
        # 新浪的列名已经是英文，只需确保有 date 列
        return df

    # 先试东方财富（各重试 2 次），失败再整体切到新浪
    try:
        df = _retry(fetch_eastmoney, times=2)
    except Exception:
        print("东方财富取数失败，切换到新浪财经...")
        df = _retry(fetch_sina, times=2)

    if df.empty:
        raise ValueError(f"没有获取到 {symbol} 的数据，请检查代码是否正确")

    # 把「日期」列设为索引，并转成日期类型（和美股格式对齐）
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    df = df[["open", "high", "low", "close", "volume"]]

    return df


def get_stock(market: str, symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    统一入口：根据市场类型自动选择对应的数据获取函数。

    参数：
        market: "美股" 或 "A股"
        symbol: 股票代码
        period: 时间范围

    返回：
        统一格式的 DataFrame。

    这种「根据参数分发到不同函数」的写法叫做「分发（dispatch）」，
    好处是界面层只需要调用 get_stock，不用关心底层用哪个数据源。
    """
    if market == "美股":
        return get_us_stock(symbol, period)
    elif market == "A股":
        return get_cn_stock(symbol, period)
    else:
        raise ValueError(f"不支持的市场类型：{market}")


# ------------------------------------------------------------
# 下面这段是「模块自测」代码。
# 只有直接运行 `python data.py` 时才会执行，
# 被别的文件 import 时不会执行（因为 __name__ 不等于 "__main__"）。
# 这是一个非常常用的技巧，方便你单独测试这个文件对不对。
# ------------------------------------------------------------
if __name__ == "__main__":
    print("测试获取苹果股票数据...")
    data = get_us_stock("AAPL", period="6mo")
    print(data.tail())      # .tail() 打印最后 5 行
    print(f"共获取 {len(data)} 条数据")
