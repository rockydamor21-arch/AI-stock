import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
            df = yf.download(sym, period=period, interval="1d", progress=False)
            if df.empty: continue
            
            # 计算短线指标
            df['EMA5'] = ta.ema(df['Close'], length=5)
            df['EMA20'] = ta.ema(df['Close'], length=20)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            bbands = ta.bbands(df['Close'], length=20, std=2)
            df = df.join(bbands)
            macd = ta.macd(df['Close'])
            df = df.join(macd)
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            vol_avg = df['Volume'].tail(5).mean()
            
            # --- 短线爆发评分算法 ---
            score = 0
            # 信号1：放量 (权重5)
            if latest['Volume'] > vol_avg * 1.5: score += 5 
            # 信号2：突破布林带上轨 (权重6)
            if latest['Close'] > latest['BBU_20_2.0']: score += 6
            # 信号3：MACD动能增强 (权重4)
            if latest['MACDh_12_26_9'] > prev['MACDh_12_26_9']: score += 4
            # 信号4：站稳短线均线 (权重3)
            if latest['Close'] > latest['EMA5']: score += 3
            
            results.append({
                "代码": sym,
                "当前价": round(latest['Close'], 2),
                "短线评分": score,
                "RSI": round(latest['RSI'], 1),
                "成交量比": f"{round(latest['Volume']/vol_avg, 2)}x",
                "状态": "🚀爆发中" if score >= 12 else "横盘蓄势" if score >= 5 else "弱势"
            })
        except Exception as e:
            st.error(f"{sym} 数据获取失败: {e}")

    # 4. 展示看板
    if results:
        res_df = pd.DataFrame(results).sort_values(by="短线评分", ascending=False)
        st.subheader("📊 实时量化筛选榜单")
        st.dataframe(res_df, use_container_width=True)
        
        # 选出最高分进行深度分析
        top_stock = res_df.iloc[0]['代码']
        st.divider()
        st.subheader(f"🔍 深度聚焦：{top_stock} 的 AI 分析报告")
        
        # 绘制该股K线图
        df_plot = yf.download(top_stock, period="3mo", interval="1d")
        fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], 
                        high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'])])
        fig.update_layout(title=f"{top_stock} 最近走势", template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # 5. 生成终极提示词
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
