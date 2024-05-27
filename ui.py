import streamlit as st
import pandas as pd
import numpy as np

# 標題
st.title("簡單的數據應用")

# 創建一個數據框
data = pd.DataFrame({
    'A': np.random.randn(50),
    'B': np.random.randn(50)
})

# 顯示數據框
st.write("數據框：", data)

# 畫圖
st.line_chart(data)

# 添加一個滑動條
slider = st.slider('選擇一個值', 0, 100, 50)
st.write('你選擇的值是:', slider)
