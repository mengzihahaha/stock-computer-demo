# ============================================================
# app.py —— Streamlit 网页界面（程序入口）
# ------------------------------------------------------------
# 职责：只负责「界面」和「把各模块串起来」，不写具体计算逻辑。
#       计算逻辑在 factors.py，取数逻辑在 data.py。
#
# 运行方式（重要！不是 python app.py，而是）：
#       streamlit run app.py
# 然后浏览器会自动打开 http://localhost:8501
#
# Streamlit 的核心思想：
#   它会「从上到下」重新运行整个脚本，每次你和页面交互
#   （点按钮、输入文字）都会重跑一遍。你只管写 Python，
#   它自动帮你变成网页，非常适合数据类小应用。
# ============================================================

import streamlit as st       # 网页框架
import pandas as pd

# 导入我们自己写的两个模块（同目录下的 data.py 和 factors.py）
import data
import factors


# ------------------------------------------------------------
# 1. 页面基础配置（必须是第一个 streamlit 命令）
# ------------------------------------------------------------
st.set_page_config(
    page_title="股票因子计算器",   # 浏览器标签页标题
    page_icon="📈",               # 标签页小图标
    layout="wide",                # 宽屏布局，图表更好看
)

# 页面大标题和说明
st.title("📈 股票因子计算器")
st.caption("输入股票代码，自动获取行情并计算常用量化因子 —— 学习项目")


# ------------------------------------------------------------
# 2. 侧边栏：放用户的输入控件
#    st.sidebar 表示把控件放到左侧栏，主区域留给图表
# ------------------------------------------------------------
with st.sidebar:
    st.header("参数设置")

    # 下拉框：选择市场。返回用户选中的那个字符串
    market = st.selectbox(
        "选择市场",
        options=["美股", "A股"],
    )

    # 根据市场给一个默认代码和提示，降低使用门槛
    if market == "美股":
        default_symbol = "AAPL"
        help_text = "美股代码，如 AAPL(苹果)、MSFT(微软)、TSLA(特斯拉)"
    else:
        default_symbol = "600519"
        help_text = "A股6位代码，如 600519(茅台)、000001(平安银行)"

    # 文本输入框：让用户输入股票代码
    symbol = st.text_input(
        "股票代码",
        value=default_symbol,     # 默认值
        help=help_text,           # 鼠标悬停时的提示
    )

    # 下拉框：选时间范围
    period = st.selectbox(
        "时间范围",
        options=["6mo", "1y", "2y", "5y"],
        index=1,                  # 默认选第 2 个，即 "1y"
    )

    # 按钮：点击后才开始获取和计算（返回 True/False）
    run = st.button("开始计算", type="primary")


# ------------------------------------------------------------
# 3. 数据获取函数 + 缓存
#    @st.cache_data 是「缓存装饰器」：
#    相同参数第二次调用时，直接返回上次结果，不再重新联网下载。
#    好处：切换因子显示时不会反复请求网络，页面更快。
# ------------------------------------------------------------
@st.cache_data(ttl=3600)   # ttl=3600 表示缓存 1 小时后过期
def load_data(market: str, symbol: str, period: str) -> pd.DataFrame:
    """封装 data.get_stock，加上缓存能力。"""
    return data.get_stock(market, symbol, period)


# ------------------------------------------------------------
# 4. 主逻辑：只有点了「开始计算」按钮才执行
# ------------------------------------------------------------
if run:
    # try/except 是「异常处理」：
    # 万一代码写错、网络断了，捕获错误并友好提示，而不是让程序崩溃。
    try:
        # st.spinner 显示一个「加载中...」的转圈提示
        with st.spinner(f"正在获取 {symbol} 的数据..."):
            df = load_data(market, symbol, period)
            df = factors.compute_all_factors(df)   # 计算所有因子

        st.success(f"成功获取 {len(df)} 条数据 ✅")

        # -------- 4.1 价格 + 均线走势图 --------
        st.subheader("价格走势（收盘价 vs 20日均线）")
        # st.line_chart 直接把 DataFrame 的这两列画成折线图
        st.line_chart(df[["close", "MA20"]])

        # -------- 4.2 用「分栏」并排展示两个因子图 --------
        # st.columns(2) 把页面横向分成 2 等份
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("动量因子（20日 %）")
            st.line_chart(df["动量_20日"])

        with col2:
            st.subheader("波动率因子（20日）")
            st.line_chart(df["波动率_20日"])

        # -------- 4.3 RSI 图 + 参考线说明 --------
        st.subheader("RSI 相对强弱指标（14日）")
        st.line_chart(df["RSI_14日"])
        st.caption("参考：RSI > 70 可能超买，< 30 可能超卖")

        # -------- 4.4 展示原始数据表格（最近 20 行）--------
        st.subheader("数据明细（最近 20 天）")
        # .tail(20) 取最后 20 行；st.dataframe 渲染成可滚动的表格
        st.dataframe(df.tail(20))

        # -------- 4.5 下载按钮：把结果导出成 CSV --------
        # 这是个实用小功能，也能让简历项目显得更完整
        csv = df.to_csv().encode("utf-8-sig")   # utf-8-sig 防止中文乱码
        st.download_button(
            label="下载完整数据 (CSV)",
            data=csv,
            file_name=f"{symbol}_factors.csv",
            mime="text/csv",
        )

    except Exception as e:
        # 出错时红色提示，并显示错误信息，方便你排查
        st.error(f"出错了：{e}")
        st.info("请检查股票代码是否正确，或稍后重试（可能是网络问题）。")

else:
    # 还没点按钮时，显示引导提示
    st.info("👈 请在左侧填写参数，然后点击「开始计算」")
