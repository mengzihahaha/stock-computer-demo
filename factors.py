# ============================================================
# factors.py —— 因子计算模块
# ------------------------------------------------------------
# 职责：输入行情 DataFrame，输出计算好的因子。
#
# 设计原则：这里所有函数都是「纯函数」——
#   - 输入相同，输出一定相同
#   - 不联网、不读写文件、不改全局变量
# 好处：
#   1. 极易测试（给定输入，断言输出即可，见 test 部分）
#   2. 逻辑清晰，别人一看就懂
# 这是面试时能体现「代码质量意识」的关键点。
#
# 什么是「因子」？
#   因子就是从价格/成交量里算出来的一个数值指标，
#   用来衡量股票的某种特征（趋势、风险、超买超卖等），
#   是量化投资里筛选股票的基础工具。
# ============================================================

import pandas as pd


def moving_average(close: pd.Series, window: int = 20) -> pd.Series:
    """
    移动平均线（MA）—— 最基础的趋势因子。

    含义：过去 window 天收盘价的平均值，用来平滑价格、看趋势方向。
         价格在 MA 上方通常视为偏强，下方偏弱。

    参数：
        close: 收盘价序列（一列数据，pandas.Series）
        window: 窗口天数，默认 20 天

    实现：
        .rolling(window) 创建一个「滑动窗口」，
        .mean() 对每个窗口求平均。
        比如 window=20，就是每天都取「含当天在内的近 20 天」求均值。
    """
    return close.rolling(window=window).mean()


def momentum(close: pd.Series, window: int = 20) -> pd.Series:
    """
    动量因子（Momentum）—— 衡量涨跌力度。

    含义：过去 window 天的累计收益率（涨了多少百分比）。
         正值表示上涨趋势，负值表示下跌。动量策略认为「强者恒强」。

    实现：
        .pct_change(window) 计算「当前值相对 window 天前的变化率」。
        结果乘 100 变成百分比，更直观。
    """
    return close.pct_change(periods=window) * 100


def volatility(close: pd.Series, window: int = 20) -> pd.Series:
    """
    波动率因子（Volatility）—— 衡量风险大小。

    含义：过去 window 天「日收益率」的标准差。
         数值越大说明价格波动越剧烈、风险越高。

    实现步骤：
        1. close.pct_change() 算出每天的涨跌幅（日收益率）
        2. .rolling(window).std() 算滑动窗口内的标准差
        标准差是统计学里衡量「数据分散程度」的指标。
    """
    daily_returns = close.pct_change()               # 第 1 步：日收益率
    return daily_returns.rolling(window=window).std()  # 第 2 步：滚动标准差


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """
    RSI 相对强弱指标 —— 衡量超买/超卖。

    含义：取值 0~100。
         通常 >70 视为「超买」（可能回调），<30 视为「超卖」（可能反弹）。

    计算逻辑（经典 14 日 RSI）：
        1. 算每日价格变化 delta
        2. 把上涨的部分和下跌的部分分开
        3. 分别算平均上涨幅度、平均下跌幅度
        4. RS = 平均涨 / 平均跌
        5. RSI = 100 - 100 / (1 + RS)

    这个因子稍复杂，是练习「多步骤数据处理」的好例子。
    """
    delta = close.diff()                    # 第 1 步：今天 - 昨天

    # 第 2 步：把涨和跌拆开
    #   where(条件, 否则填的值)：不满足条件的位置填 0
    gain = delta.where(delta > 0, 0.0)      # 只保留上涨（跌的填 0）
    loss = -delta.where(delta < 0, 0.0)     # 只保留下跌并取正数

    # 第 3 步：分别求滚动平均
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    # 第 4 步：相对强度 RS（加一个极小值防止除以 0）
    rs = avg_gain / (avg_loss + 1e-10)

    # 第 5 步：套公式得到 RSI
    return 100 - (100 / (1 + rs))


def compute_all_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    一次性计算所有因子，并拼接到原始数据后面。

    参数：
        df: 包含 close 列的行情 DataFrame（来自 data.py）

    返回：
        在原始 df 基础上，新增几列因子的 DataFrame。

    这个函数是「组合」上面几个小函数，体现了
    「用小的、单一功能的函数搭出复杂功能」的编程思路。
    """
    # .copy() 复制一份，避免直接修改传进来的原始数据（好习惯，防止副作用）
    result = df.copy()

    close = df["close"]                          # 取出收盘价列

    result["MA20"] = moving_average(close, 20)   # 20 日均线
    result["动量_20日"] = momentum(close, 20)     # 20 日动量
    result["波动率_20日"] = volatility(close, 20) # 20 日波动率
    result["RSI_14日"] = rsi(close, 14)          # 14 日 RSI

    return result


# ------------------------------------------------------------
# 模块自测：直接运行 `python factors.py` 时执行。
# 这里用「造假数据」测试，不联网，展示纯函数好测试的优点。
# ------------------------------------------------------------
if __name__ == "__main__":
    # 造一段简单的收盘价：1,2,3,...,30
    test_close = pd.Series(range(1, 31), dtype="float64")

    print("测试 5 日均线：")
    print(moving_average(test_close, window=5).tail())

    # 因为价格一路上涨，动量应该是正数，RSI 应该接近 100
    print("\n测试动量（应为正数）：")
    print(momentum(test_close, window=5).tail())
