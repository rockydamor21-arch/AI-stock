import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import pandas as pd

# 1. 页面基础设置
st.set_page_config(page_title="AI短线雷达", layout="wide")
st.title("🚀 AI 短线爆发量化分析仪")

# 2. 侧边栏配置
st.sidebar.header("配置中心")
symbols_input = st.sidebar.text_input("输入股票代码 (英文逗号分隔)", "NVDA, TSLA, AAPL, AMD, MSFT")
symbols = [s.strip().upper() for s in symbols_input.split(",")]
period = st.sidebar.selectbox("分析周期", ["1mo", "3mo", "6mo"], index=1)

# 3. 核心计算与扫描逻辑
if st.sidebar.button("开始全量扫描"):
    results = []

    for sym in symbols:
        try:
            # 下载数据
            ticker = yf.Ticker(sym)
            df = ticker.history(period=period, interval="1d")
            if df is None or df.empty:
                st.warning(f"{sym} 无数据，跳过")
                continue

            # 重置列名（兼容新版yfinance多级列名）
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.dropna(inplace=True)

            close = df['Close']
            volume = df['Volume']

            # 计算指标
            df['EMA5'] = ta.ema(close, length=5)
            df['RSI'] = ta.rsi(close, length=14)
            bbands = ta.bbands(close, length=20, std=2)
            macd = ta.macd(close)

            if bbands is not None:
                df = pd.concat([df, bbands], axis=1)
            if macd is not None:
                df = pd.concat([df, macd], axis=1)

            df.dropna(inplace=True)
            if len(df) < 2:
                st.warning(f"{sym} 数据不足，跳过")
                continue

            latest = df.iloc[-1]
            prev = df.iloc[-2]
            vol_avg = volume.tail(5).mean()

            # 短线爆发评分
            score = 0
            if latest['Volume'] > vol_avg * 1.5: score += 5
            bbu_col = [c for c in df.columns if c.startswith('BBU')]
            macdh_col = [c for c in df.columns if c.startswith('MACDh')]
            if bbu_col and latest['Close'] > latest[bbu_col[0]]: score += 6
            if macdh_col and latest[macdh_col[0]] > prev[macdh_col[0]]: score += 4
            if latest['Close'] > latest['EMA5']: score += 3

            results.append({
                "代码": sym,
                "当前价": round(float(latest['Close']), 2),
                "短线评分": score,
                "RSI": round(float(latest['RSI']), 1),
                "成交量比": f"{round(float(latest['Volume'])/float(vol_avg), 2)}x",
                "状态": "🚀爆发中" if score >= 12 else "横盘蓄势" if score >= 5 else "弱势"
            })

        except Exception as e:
            st.error(f"{sym} 数据获取失败: {e}")

    # 4. 展示看板
    if results:
        res_df = pd.DataFrame(results).sort_values(by="短线评分", ascending=False)
        st.subheader("📊 实时量化筛选榜单")
        st.dataframe(res_df, use_container_width=True)

        top_stock = res_df.iloc[0]['代码']
        st.divider()
        st.subheader(f"🔍 深度聚焦：{top_stock} 的 AI 分析报告")

        # 绘制K线图
        df_plot = yf.Ticker(top_stock).history(period="3mo", interval="1d")
        df_plot.columns = [c[0] if isinstance(c, tuple) else c for c in df_plot.columns]
        fig = go.Figure(data=[go.Candlestick(
            x=df_plot.index,
            open=df_plot['Open'],
            high=df_plot['High'],
            low=df_plot['Low'],
            close=df_plot['Close']
        )])
        fig.update_layout(title=f"{top_stock} 最近走势", template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 生成提示词
        latest_top = res_df.iloc[0]
        prompt = f"""
# 角色：短线游资操盘手
# 任务：分析股票 {top_stock} 的短线真伪突破。

## 数据事实：
- 评分：{latest_top['短线评分']} (总分18)
- RSI：{latest_top['RSI']}
- 成交量：较5日均值放大 {latest_top['成交量比']}

## 请分析：
1. 这种放量突破是否具备持续性？
2. 给出一个'分批入场'的点位建议。
3. 如果明天跌破哪一个价位，说明本次爆发失败，必须斩仓？
        """
        st.text_area("📋 复制此内容发送给 AI：", value=prompt, height=200)
