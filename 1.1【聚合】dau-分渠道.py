"""
天气数据分析平台 - Weather Data Analytics
========================================

环境要求:
- Python 3.8+
- streamlit >= 1.28.0
- pandas >= 1.5.0
- numpy >= 1.20.0
- openpyxl >= 3.0.0

说明: 其他依赖包将自动安装
"""

import streamlit as st
import pandas as pd
import datetime
import re
import io
import numpy as np
import warnings
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

# 自动安装依赖包函数
@st.cache_resource
def install_and_import_packages():
    """自动安装并导入所需的包"""
    packages_to_install = []
    
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
    except ImportError:
        packages_to_install.append('matplotlib')
    
    try:
        import seaborn as sns
    except ImportError:
        packages_to_install.append('seaborn')
    
    # 如果需要安装包
    if packages_to_install:
        with st.spinner(f"正在自动安装依赖包: {', '.join(packages_to_install)}..."):
            for package in packages_to_install:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                        stdout=subprocess.DEVNULL, 
                                        stderr=subprocess.DEVNULL)
                except Exception as e:
                    st.warning(f"自动安装 {package} 失败，将使用替代方案")
    
    # 重新导入
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import seaborn as sns
        return plt, mdates, sns, True
    except ImportError:
        return None, None, None, False

# 尝试自动安装和导入
plt, mdates, sns, has_matplotlib = install_and_import_packages()

# 忽略警告
warnings.filterwarnings('ignore')

# 页面配置
st.set_page_config(
    page_title="Weather Data Analytics",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 天气主题CSS样式
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #4facfe 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
        min-height: 100vh;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .weather-header {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 24px;
        padding: 3rem 2rem;
        margin: 2rem 0;
        text-align: center;
        color: white;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .weather-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: float 6s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-20px) rotate(180deg); }
    }
    
    .weather-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .weather-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 16px 48px rgba(0, 0, 0, 0.15);
    }
    
    .weather-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        border-radius: 20px 20px 0 0;
    }
    
    .metric-weather {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-weather:hover {
        transform: scale(1.02);
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);
    }
    
    .metric-weather h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
        margin: 0;
        background: linear-gradient(90deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .metric-weather p {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: #666;
        margin: 0.5rem 0 0 0;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .upload-zone {
        background: rgba(255, 255, 255, 0.9);
        border: 2px dashed rgba(102, 126, 234, 0.4);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .upload-zone:hover {
        border-color: rgba(102, 126, 234, 0.8);
        background: rgba(255, 255, 255, 0.95);
        transform: translateY(-2px);
    }
    
    .success-weather {
        background: linear-gradient(135deg, rgba(86, 171, 47, 0.1) 0%, rgba(168, 230, 207, 0.1) 100%);
        border: 1px solid rgba(86, 171, 47, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: #2d5016;
        backdrop-filter: blur(10px);
    }
    
    .weather-tabs .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(255, 255, 255, 0.1);
        padding: 6px;
        border-radius: 16px;
        backdrop-filter: blur(10px);
    }
    
    .weather-tabs .stTabs [data-baseweb="tab"] {
        height: 50px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        color: white;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    
    .weather-tabs .stTabs [aria-selected="true"] {
        background: rgba(255, 255, 255, 0.9);
        color: #667eea;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 16px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-family: 'Inter', sans-serif;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
        background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
    }
    
    .weather-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        display: block;
        animation: bounce 2s infinite;
    }
    
    @keyframes bounce {
        0%, 20%, 53%, 80%, 100% { transform: translate3d(0,0,0); }
        40%, 43% { transform: translate3d(0,-8px,0); }
        70% { transform: translate3d(0,-4px,0); }
        90% { transform: translate3d(0,-2px,0); }
    }
    
    .weather-subtitle {
        font-family: 'Inter', sans-serif;
        font-weight: 300;
        font-size: 1.2rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    .weather-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 3.5rem;
        margin: 0;
        text-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    
    .download-btn {
        background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        margin: 0.3rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(86, 171, 47, 0.3);
    }
    
    .floating-particles {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
    }
    
    .particle {
        position: absolute;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 50%;
        animation: floatUp 15s infinite linear;
    }
    
    @keyframes floatUp {
        0% {
            opacity: 0;
            transform: translateY(100vh) scale(0);
        }
        10% {
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        100% {
            opacity: 0;
            transform: translateY(-100vh) scale(1);
        }
    }
    
    .data-preview {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 16px;
        padding: 1rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    }
</style>

<!-- 浮动粒子效果 -->
<div class="floating-particles">
    <div class="particle" style="left: 10%; width: 4px; height: 4px; animation-delay: 0s;"></div>
    <div class="particle" style="left: 20%; width: 6px; height: 6px; animation-delay: 2s;"></div>
    <div class="particle" style="left: 30%; width: 3px; height: 3px; animation-delay: 4s;"></div>
    <div class="particle" style="left: 40%; width: 5px; height: 5px; animation-delay: 6s;"></div>
    <div class="particle" style="left: 50%; width: 4px; height: 4px; animation-delay: 8s;"></div>
    <div class="particle" style="left: 60%; width: 6px; height: 6px; animation-delay: 10s;"></div>
    <div class="particle" style="left: 70%; width: 3px; height: 3px; animation-delay: 12s;"></div>
    <div class="particle" style="left: 80%; width: 5px; height: 5px; animation-delay: 14s;"></div>
    <div class="particle" style="left: 90%; width: 4px; height: 4px; animation-delay: 16s;"></div>
</div>
""", unsafe_allow_html=True)

def convert_date_to_sortable(date_str: str) -> str:
    """将日期字符串转换为可排序的格式"""
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            year, month, day = parts
            month = month.zfill(2)
            day = day.zfill(2)
            return f"{year}{month}{day}"
    except:
        pass
    return date_str

def force_standardize_date(date_str):
    """强制标准化日期格式，确保月份和日期都是两位数"""
    if pd.isna(date_str) or str(date_str).strip() == '':
        return date_str

    date_str = str(date_str).strip()

    # 处理不同分隔符，统一转换为/
    if '-' in date_str:
        date_str = date_str.replace('-', '/')

    # 如果包含/，则处理
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            try:
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                # 强制格式化为两位数
                result = f"{year:04d}/{month:02d}/{day:02d}"
                return result
            except:
                pass

    return date_str

def create_weather_visualization(df, title, chart_type="line"):
    """创建天气主题的数据可视化图表"""
    try:
        if df.empty:
            return None
            
        # 获取日期列（通常是第一列）
        date_col = df.columns[0]
        
        # 尝试转换日期格式
        try:
            df_viz = df.copy()
            df_viz[date_col] = pd.to_datetime(df_viz[date_col], errors='coerce')
            df_viz = df_viz.dropna(subset=[date_col])
            df_viz = df_viz.sort_values(date_col)
        except:
            df_viz = df.copy()
        
        # 如果matplotlib可用，使用matplotlib
        if has_matplotlib and plt is not None:
            return create_matplotlib_chart(df_viz, title, chart_type, date_col)
        else:
            # 使用Streamlit内置图表作为备选方案
            return create_streamlit_chart(df_viz, title, chart_type, date_col)
            
    except Exception as e:
        st.warning(f"图表创建失败: {str(e)}")
        return None

def create_matplotlib_chart(df_viz, title, chart_type, date_col):
    """使用matplotlib创建图表"""
    # 天气主题配色
    colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b']
    
    if chart_type == "line":
        # 寻找数值列
        numeric_cols = df_viz.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) > 0:
            fig, ax = plt.subplots(figsize=(12, 6))
            fig.patch.set_facecolor('white')
            fig.patch.set_alpha(0.9)
            
            # 添加多个数值列的线图
            for i, col in enumerate(numeric_cols[:5]):
                valid_data = df_viz[[date_col, col]].dropna()
                if not valid_data.empty:
                    ax.plot(valid_data[date_col], valid_data[col], 
                           color=colors[i % len(colors)], 
                           linewidth=3, 
                           marker='o', 
                           markersize=6,
                           label=col,
                           alpha=0.8)
            
            ax.set_title(title, fontsize=16, fontweight='bold', color='#333', pad=20)
            ax.set_xlabel('日期', fontsize=12, color='#666')
            ax.set_ylabel('数值', fontsize=12, color='#666')
            
            # 美化样式
            ax.grid(True, alpha=0.3)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#ddd')
            ax.spines['bottom'].set_color('#ddd')
            
            if len(numeric_cols) > 1:
                ax.legend(loc='upper left', frameon=False)
            
            # 格式化x轴日期
            if df_viz[date_col].dtype == 'datetime64[ns]' and mdates is not None:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            return fig
            
    elif chart_type == "bar":
        # 创建柱状图
        if '三端' in df_viz.columns:
            # 按渠道分组统计
            numeric_cols = df_viz.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                agg_data = df_viz.groupby('三端')[numeric_cols[0]].sum().reset_index()
                
                fig, ax = plt.subplots(figsize=(10, 6))
                fig.patch.set_facecolor('white')
                fig.patch.set_alpha(0.9)
                
                bars = ax.bar(agg_data['三端'], agg_data[numeric_cols[0]], 
                             color=colors[:len(agg_data)], 
                             alpha=0.8,
                             edgecolor='white',
                             linewidth=2)
                
                ax.set_title(title, fontsize=16, fontweight='bold', color='#333', pad=20)
                ax.set_xlabel('渠道', fontsize=12, color='#666')
                ax.set_ylabel(numeric_cols[0], fontsize=12, color='#666')
                
                # 美化样式
                ax.grid(True, alpha=0.3, axis='y')
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_color('#ddd')
                ax.spines['bottom'].set_color('#ddd')
                
                # 在柱子上显示数值
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:,.0f}',
                           ha='center', va='bottom', fontweight='bold')
                
                plt.tight_layout()
                return fig
    
    return None

def create_streamlit_chart(df_viz, title, chart_type, date_col):
    """使用Streamlit内置图表作为备选方案"""
    st.subheader(title)
    
    if chart_type == "line":
        # 寻找数值列
        numeric_cols = df_viz.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) > 0:
            # 准备数据用于st.line_chart
            chart_data = df_viz.set_index(date_col)[numeric_cols[:5]]
            st.line_chart(chart_data, height=400)
            return "streamlit_chart"
            
    elif chart_type == "bar":
        if '三端' in df_viz.columns:
            numeric_cols = df_viz.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                agg_data = df_viz.groupby('三端')[numeric_cols[0]].sum().reset_index()
                agg_data = agg_data.set_index('三端')
                st.bar_chart(agg_data, height=400)
                return "streamlit_chart"
    
    return None

def process_dau_files(uploaded_files) -> Optional[Dict[str, pd.DataFrame]]:
    """处理DAU文件上传"""
    if not uploaded_files:
        return None
        
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    channel_dfs = {'mvp': [], 'and': [], 'ios': []}
    standard_columns = {'mvp': None, 'and': None, 'ios': None}
    
    processed_files = 0
    total_files = len(uploaded_files)
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"🌤️ 正在处理: {uploaded_file.name} ({i+1}/{total_files})")
            
            filename = uploaded_file.name
            
            if "dau" not in filename.lower():
                continue
            
            # 从文件名中提取渠道信息
            if len(filename) > 7 and filename.startswith("dau_"):
                channel = filename[4:7]  # 获取渠道名 (mvp, and, ios)
                if channel not in channel_dfs:
                    continue
            else:
                continue
            
            # 读取CSV文件
            try:
                content = uploaded_file.getvalue()
                try:
                    df = pd.read_csv(io.StringIO(content.decode('utf-8')), 
                                   na_values=[''], keep_default_na=False)
                except UnicodeDecodeError:
                    df = pd.read_csv(io.StringIO(content.decode('latin1')), 
                                   na_values=[''], keep_default_na=False)
                
            except Exception as e:
                continue
            
            if df.empty:
                continue
            
            # 删除指定的三列
            columns_to_drop = ['Total Conversions', 'Re-attribution', 'Re-engagement']
            df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')
            
            # 从文件名提取日期
            try:
                date_part = filename.split('_')[-1].replace('.csv', '')
                match = re.search(r'(\d+)\.(\d+)', date_part)
                if match:
                    month, day = match.groups()
                    formatted_date = f"2025/{month}/{day}"
                else:
                    formatted_date = date_part
            except:
                formatted_date = "2025/1/1"
            
            # 添加日期列
            df.insert(0, 'date', formatted_date)
            
            # iOS特殊处理
            if channel == 'ios' and 'Average eCPIUS$2.50' in df.columns:
                df = df.drop(columns=['Average eCPIUS$2.50'])
            
            # 列标准化
            if standard_columns[channel] is None:
                standard_columns[channel] = df.columns.tolist()
            else:
                current_cols = df.columns.tolist()
                if current_cols != standard_columns[channel]:
                    missing_cols = [col for col in standard_columns[channel] if col not in current_cols]
                    extra_cols = [col for col in current_cols if col not in standard_columns[channel]]
                    
                    if missing_cols:
                        for col in missing_cols:
                            df[col] = 'N/A'
                    
                    if extra_cols:
                        df = df.drop(columns=extra_cols)
                    
                    df = df[standard_columns[channel]]
            
            df = df.fillna('N/A')
            channel_dfs[channel].append(df)
            processed_files += 1
            
        except Exception as e:
            continue
    
    progress_bar.progress(1.0)
    status_text.text(f"☀️ DAU文件处理完成! 成功处理了 {processed_files} 个文件")
    
    if processed_files == 0:
        return None
    
    # 合并数据
    merged_by_channel = {}
    
    for channel, df_list in channel_dfs.items():
        if df_list:
            # 确保列一致性
            if len(df_list) > 1:
                standard_cols = list(df_list[0].columns)
                for i, df in enumerate(df_list):
                    if set(df.columns) != set(standard_cols):
                        missing = [col for col in standard_cols if col not in df.columns]
                        extra = [col for col in df.columns if col not in standard_cols]
                        
                        for col in missing:
                            df[col] = 'N/A'
                        if extra:
                            df = df.drop(columns=extra)
                        df = df[standard_cols]
                        df_list[i] = df
            
            merged_df = pd.concat(df_list, ignore_index=True)
            
            # 按日期排序
            try:
                merged_df['sort_key'] = merged_df['date'].apply(convert_date_to_sortable)
                merged_df = merged_df.sort_values(by='sort_key')
                merged_df = merged_df.drop(columns=['sort_key'])
            except Exception as e:
                pass
            
            merged_df = merged_df.fillna('N/A')
            
            # iOS特殊处理
            if channel == 'ios':
                expected_columns = ['date', 'Country', 'Impressions', 'Clicks', 'Installs', 'Conversion Rate',
                                  'Activity Sessions', 'Cost', 'Activity Revenue', 'Average eCPIUS$2.31',
                                  'Average DAU', 'Average MAU', 'Average DAU/MAU Rate', 'ARPDAU']
                
                extra_columns = [col for col in merged_df.columns if col not in expected_columns]
                if extra_columns:
                    merged_df = merged_df.drop(columns=extra_columns)
                
                missing_columns = [col for col in expected_columns if col not in merged_df.columns]
                if missing_columns:
                    for col in missing_columns:
                        merged_df[col] = 'N/A'
                
                merged_df = merged_df[expected_columns]
            
            merged_by_channel[channel] = merged_df
    
    return merged_by_channel

def process_retention_files(uploaded_files) -> Optional[Dict[str, pd.DataFrame]]:
    """处理留存文件上传"""
    if not uploaded_files:
        return None
        
    # 渠道配置
    channels_config = {
        'ios': {
            'pattern': 'retention_ios.csv',
            'empty_columns': 4,
            'days': list(range(1, 8)) + [14, 30]
        },
        'ios_formal': {
            'pattern': 'retention_ios_formal.csv',
            'empty_columns': 4,
            'days': list(range(1, 8)) + [14, 30]
        },
        'mvp': {
            'pattern': 'retention_mvp.csv',
            'empty_columns': 1,
            'days': list(range(1, 8)) + [14]
        },
        'and': {
            'pattern': 'retention_and.csv',
            'empty_columns': 0,
            'days': list(range(1, 8)) + [14, 30]
        }
    }
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    processed_data = {}
    total_files = len(uploaded_files)
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"🌧️ 正在处理: {uploaded_file.name} ({i+1}/{total_files})")
            
            filename = uploaded_file.name.lower()
            
            # 匹配渠道
            channel = None
            for ch, config in channels_config.items():
                if config['pattern'].lower() in filename:
                    channel = ch
                    break
            
            if not channel:
                continue
            
            # 读取文件
            try:
                content = uploaded_file.getvalue()
                encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']
                df = None
                
                for encoding in encodings:
                    try:
                        df = pd.read_csv(io.StringIO(content.decode(encoding)))
                        break
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    continue
                
            except Exception as e:
                continue
            
            # 处理日期列
            date_column = "Cohort Day"
            if date_column not in df.columns:
                possible_date_columns = ['Date', 'date', '日期', 'DAY', 'Day', 'day']
                for col in possible_date_columns:
                    if col in df.columns:
                        date_column = col
                        break
                
                if date_column not in df.columns:
                    continue
            
            # 排序数据
            try:
                df[date_column] = pd.to_datetime(df[date_column])
                df = df.sort_values(by=date_column)
            except:
                try:
                    df = df.sort_values(by=date_column)
                except:
                    pass
            
            # 检查用户列
            users_column = 'Users'
            if users_column not in df.columns:
                possible_users_columns = ['users', '用户数', 'DAU', 'User Count', 'user_count']
                for col in possible_users_columns:
                    if col in df.columns:
                        users_column = col
                        break
                
                if users_column not in df.columns:
                    continue
            
            # 添加空列
            config = channels_config[channel]
            for j in range(config['empty_columns']):
                df[' ' * (j + 1)] = None
            
            # 计算留存率
            for day in config['days']:
                retention_column = f'sessions - Unique users - day {day} - partial'
                alternative_column = f'sessions - Unique users - day {day}'
                
                if retention_column in df.columns:
                    df[f'day{day}'] = (df[retention_column] / df[users_column]).round(4)
                elif alternative_column in df.columns:
                    df[retention_column] = df[alternative_column]
                    df[f'day{day}'] = (df[retention_column] / df[users_column]).round(4)
            
            processed_data[channel] = df
            
        except Exception as e:
            continue
    
    progress_bar.progress(1.0)
    status_text.text(f"⛅ 留存文件处理完成! 成功处理了 {len(processed_data)} 个文件")
    
    return processed_data if processed_data else None

def create_integrated_dau(merged_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """整合三个渠道的DAU数据"""
    if not merged_data:
        return pd.DataFrame()
    
    integrated_dfs = []
    
    for channel, df in merged_data.items():
        df_copy = df.copy()
        # 映射渠道名
        channel_mapping = {'and': 'android', 'mvp': 'mvp', 'ios': 'ios'}
        df_copy.insert(1, '三端', channel_mapping.get(channel, channel))
        integrated_dfs.append(df_copy)
    
    if not integrated_dfs:
        return pd.DataFrame()
    
    try:
        # 统一列
        all_columns = []
        for df in integrated_dfs:
            all_columns.extend(df.columns.tolist())
        
        unique_columns = list(dict.fromkeys(all_columns))
        
        standardized_dfs = []
        for df in integrated_dfs:
            df_copy = df.copy()
            
            for col in unique_columns:
                if col not in df_copy.columns:
                    df_copy[col] = 'N/A'
            
            df_copy = df_copy[unique_columns]
            standardized_dfs.append(df_copy)
        
        integrated_df = pd.concat(standardized_dfs, ignore_index=True)
        
        # 统一日期格式
        if 'date' in integrated_df.columns:
            integrated_df['date'] = integrated_df['date'].apply(force_standardize_date)
        
        # 排序
        try:
            integrated_df['sort_key'] = integrated_df['date'].apply(convert_date_to_sortable)
            channel_order = {"mvp": 0, "android": 1, "ios": 2}
            integrated_df["渠道排序"] = integrated_df["三端"].map(channel_order)
            integrated_df = integrated_df.sort_values(by=['sort_key', '渠道排序'])
            integrated_df = integrated_df.drop(columns=['sort_key', '渠道排序'])
        except Exception as e:
            pass
        
        integrated_df = integrated_df.fillna('N/A')
        
        # 只保留前15列加三端列
        if len(integrated_df.columns) > 16:
            first_15_cols = integrated_df.iloc[:, :15].columns.tolist()
            if "三端" in integrated_df.columns and "三端" not in first_15_cols:
                cols_to_keep = first_15_cols + ["三端"]
                integrated_df = integrated_df[cols_to_keep]
        
        return integrated_df
        
    except Exception as e:
        return pd.DataFrame()

def create_integrated_retention(retention_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """整合留存数据"""
    if not retention_data:
        return pd.DataFrame()
    
    integrated_dfs = []
    
    # 渠道映射
    channel_mapping = {'and': 'android', 'mvp': 'mvp', 'ios': 'ios', 'ios_formal': 'ios'}
    
    # 期望的列顺序
    expected_columns = [
        "Cohort Day", "Ltv Country", "Campaign Id", "Keywords", "Users", "Cost", "Average eCPI",
        "sessions - Unique users - day 1 - partial", "sessions - Unique users - day 2 - partial",
        "sessions - Unique users - day 3 - partial", "sessions - Unique users - day 4 - partial",
        "sessions - Unique users - day 5 - partial", "sessions - Unique users - day 6 - partial",
        "sessions - Unique users - day 7 - partial", "sessions - Unique users - day 14 - partial",
        "sessions - Unique users - day 30 - partial", "Unnamed: 16", "Unnamed: 17", "Unnamed: 18",
        "day1", "day2", "day3", "day4", "day5", "day6", "day7", "day14", "day30",
        "三端"
    ]
    
    for channel, df in retention_data.items():
        df_copy = df.copy()
        
        # 映射渠道名
        mapped_channel = channel_mapping.get(channel, channel)
        df_copy["三端"] = mapped_channel
        
        # 列名修正
        if channel in ["mvp", "and"]:
            alt_day14 = "sessions - Unique users - day 14- partial"
            std_day14 = "sessions - Unique users - day 14 - partial"
            if alt_day14 in df_copy.columns and std_day14 not in df_copy.columns:
                df_copy = df_copy.rename(columns={alt_day14: std_day14})
            
            alt_day30 = "sessions - Unique users - day 30- partial"
            std_day30 = "sessions - Unique users - day 30 - partial"
            if alt_day30 in df_copy.columns and std_day30 not in df_copy.columns:
                df_copy = df_copy.rename(columns={alt_day30: std_day30})
        
        integrated_dfs.append(df_copy)
    
    if not integrated_dfs:
        return pd.DataFrame()
    
    try:
        # 合并数据
        integrated_df = pd.concat(integrated_dfs, ignore_index=True)
        
        # 统一日期格式
        if "Cohort Day" in integrated_df.columns:
            integrated_df["Cohort Day"] = integrated_df["Cohort Day"].apply(force_standardize_date)
        
        # 重新排序列并填充缺失列
        final_columns = []
        for col in expected_columns:
            if col not in integrated_df.columns:
                integrated_df[col] = None
            final_columns.append(col)
        
        existing_cols = [col for col in final_columns if col in integrated_df.columns]
        integrated_df = integrated_df[existing_cols]
        
        # 清空Unnamed列
        unnamed_cols = [col for col in integrated_df.columns if 'Unnamed' in col]
        for col in unnamed_cols:
            integrated_df[col] = ''
        
        # 排序
        try:
            channel_order = {"mvp": 0, "android": 1, "ios": 2}
            integrated_df["渠道排序"] = integrated_df["三端"].map(channel_order)
            integrated_df = integrated_df.sort_values(by=["Cohort Day", "渠道排序"])
            integrated_df = integrated_df.drop(columns=["渠道排序"])
        except Exception as e:
            pass
        
        integrated_df = integrated_df.fillna('N/A')
        
        return integrated_df
        
    except Exception as e:
        return pd.DataFrame()

def main():
    # 天气主题标题
    st.markdown("""
    <div class="weather-header">
        <div class="weather-icon">🌤️</div>
        <h1 class="weather-title">Weather Data Analytics</h1>
        <p class="weather-subtitle">墨迹天气数据分析平台 · 智能处理 · 深度洞察</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 核心功能区域
    st.markdown("## ☀️ 数据处理中心")
    
    # 创建两列布局
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("""
        <div class="weather-card">
            <div class="weather-icon">📊</div>
            <h3>DAU数据分析</h3>
            <p style="color: #666; margin-bottom: 1.5rem;">
                • 智能文件识别与解析<br>
                • 多渠道数据自动合并<br>
                • 实时趋势分析与预测
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # DAU文件上传区域
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        dau_files = st.file_uploader(
            "🌤️ 拖入DAU数据文件",
            type=['csv'],
            accept_multiple_files=True,
            help="支持格式: dau_渠道_日期.csv",
            key="dau_uploader",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        if dau_files:
            st.markdown(f"""
            <div class="success-weather">
                ✨ 已选择 <strong>{len(dau_files)}</strong> 个DAU文件，准备开始分析
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 开始DAU数据分析", type="primary", key="process_dau"):
                with st.spinner("🔄 正在进行智能数据分析..."):
                    st.session_state.dau_results = process_dau_files(dau_files)
                
                if st.session_state.dau_results:
                    st.balloons()
                    st.markdown("""
                    <div class="success-weather">
                        🎉 DAU数据分析完成！已生成完整的可视化报告和趋势分析
                    </div>
                    """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="weather-card">
            <div class="weather-icon">🔄</div>
            <h3>留存数据分析</h3>
            <p style="color: #666; margin-bottom: 1.5rem;">
                • 自动计算多日留存率<br>
                • 渠道留存表现对比<br>
                • 用户行为深度分析
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 留存文件上传区域
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        retention_files = st.file_uploader(
            "🌧️ 拖入留存数据文件",
            type=['csv'],
            accept_multiple_files=True,
            help="支持格式: retention_渠道.csv",
            key="retention_uploader",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        if retention_files:
            st.markdown(f"""
            <div class="success-weather">
                ✨ 已选择 <strong>{len(retention_files)}</strong> 个留存文件，准备开始分析
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 开始留存数据分析", type="primary", key="process_retention"):
                with st.spinner("🔄 正在进行智能留存分析..."):
                    st.session_state.retention_results = process_retention_files(retention_files)
                
                if st.session_state.retention_results:
                    st.balloons()
                    st.markdown("""
                    <div class="success-weather">
                        🎉 留存数据分析完成！已生成留存率趋势和用户行为洞察
                    </div>
                    """, unsafe_allow_html=True)
    
    # DAU数据可视化和结果展示
    if 'dau_results' in st.session_state and st.session_state.dau_results:
        st.markdown("---")
        st.markdown("## 📈 DAU数据洞察报告")
        
        # 创建整合数据
        integrated_dau = create_integrated_dau(st.session_state.dau_results)
        
        if not integrated_dau.empty:
            # 关键指标仪表板
            metric_cols = st.columns(4)
            with metric_cols[0]:
                st.markdown(f"""
                <div class="metric-weather">
                    <h3>{len(st.session_state.dau_results)}</h3>
                    <p>数据渠道</p>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[1]:
                total_rows = sum(len(df) for df in st.session_state.dau_results.values())
                st.markdown(f"""
                <div class="metric-weather">
                    <h3>{total_rows:,}</h3>
                    <p>数据记录</p>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[2]:
                st.markdown(f"""
                <div class="metric-weather">
                    <h3>{len(integrated_dau):,}</h3>
                    <p>整合记录</p>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_cols[3]:
                if 'Installs' in integrated_dau.columns:
                    # 尝试转换安装量为数值
                    try:
                        install_col = integrated_dau['Installs'].replace('N/A', '0')
                        install_col = install_col.astype(str).str.replace(',', '')
                        total_installs = pd.to_numeric(install_col, errors='coerce').sum()
                        if pd.isna(total_installs):
                            total_installs = 0
                    except:
                        total_installs = 0
                    
                    st.markdown(f"""
                    <div class="metric-weather">
                        <h3>{total_installs:,.0f}</h3>
                        <p>总安装量</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # 数据可视化图表
            st.markdown("### 📊 可视化分析")
            viz_cols = st.columns(2, gap="large")
            
            with viz_cols[0]:
                st.markdown('<div class="data-preview">', unsafe_allow_html=True)
                fig_line = create_weather_visualization(integrated_dau, "📈 DAU趋势分析", "line")
                if fig_line == "streamlit_chart":
                    pass  # 图表已经通过streamlit显示
                elif fig_line:
                    st.pyplot(fig_line, use_container_width=True)
                    plt.close(fig_line)  # 释放内存
                st.markdown('</div>', unsafe_allow_html=True)
            
            with viz_cols[1]:
                st.markdown('<div class="data-preview">', unsafe_allow_html=True)
                fig_bar = create_weather_visualization(integrated_dau, "🔍 渠道对比分析", "bar")
                if fig_bar == "streamlit_chart":
                    pass  # 图表已经通过streamlit显示
                elif fig_bar:
                    st.pyplot(fig_bar, use_container_width=True)
                    plt.close(fig_bar)  # 释放内存
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 数据预览表格
            st.markdown("### 📋 数据预览")
            st.markdown('<div class="weather-tabs">', unsafe_allow_html=True)
            preview_tabs = st.tabs(["🎯 三端DAU汇总"] + [f"🌤️ {ch.upper()}渠道" for ch in st.session_state.dau_results.keys()])
            st.markdown('</div>', unsafe_allow_html=True)
            
            with preview_tabs[0]:
                st.markdown('<div class="data-preview">', unsafe_allow_html=True)
                st.dataframe(
                    integrated_dau.head(15), 
                    use_container_width=True,
                    hide_index=True
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            for i, (channel, df) in enumerate(st.session_state.dau_results.items()):
                with preview_tabs[i + 1]:
                    st.markdown('<div class="data-preview">', unsafe_allow_html=True)
                    st.dataframe(
                        df.head(15), 
                        use_container_width=True,
                        hide_index=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # 下载区域
            st.markdown("### 💾 数据导出")
            download_cols = st.columns([2, 1, 1, 1, 1])
            
            today = datetime.datetime.now().strftime("%m.%d")
            
            with download_cols[0]:
                csv_data = integrated_dau.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下载三端DAU汇总数据",
                    data=csv_data.encode('utf-8-sig'),
                    file_name=f"{today}_三端DAU汇总.csv",
                    mime="text/csv",
                    type="primary"
                )
            
            # 分渠道下载
            for i, (channel, df) in enumerate(st.session_state.dau_results.items()):
                col_idx = (i + 1) % 4 + 1
                with download_cols[col_idx]:
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"{channel.upper()}",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today}_DAU_{channel}.csv",
                        mime="text/csv",
                        key=f"dau_{channel}"
                    )
    
    # 留存数据可视化
    if 'retention_results' in st.session_state and st.session_state.retention_results:
        st.markdown("---")
        st.markdown("## 🔄 留存数据洞察报告")
        
        # 创建整合数据
        integrated_retention = create_integrated_retention(st.session_state.retention_results)
        
        if not integrated_retention.empty:
            # 留存数据指标
            retention_metric_cols = st.columns(3)
            with retention_metric_cols[0]:
                st.markdown(f"""
                <div class="metric-weather">
                    <h3>{len(st.session_state.retention_results)}</h3>
                    <p>留存渠道</p>
                </div>
                """, unsafe_allow_html=True)
            
            with retention_metric_cols[1]:
                total_users = 0
                if 'Users' in integrated_retention.columns:
                    try:
                        users_col = integrated_retention['Users'].replace('N/A', '0')
                        users_col = users_col.astype(str).str.replace(',', '')
                        total_users = pd.to_numeric(users_col, errors='coerce').sum()
                        if pd.isna(total_users):
                            total_users = 0
                    except:
                        total_users = 0
                
                st.markdown(f"""
                <div class="metric-weather">
                    <h3>{total_users:,.0f}</h3>
                    <p>总用户数</p>
                </div>
                """, unsafe_allow_html=True)
            
            with retention_metric_cols[2]:
                avg_retention = 0
                day1_cols = [col for col in integrated_retention.columns if 'day1' in col.lower()]
                if day1_cols:
                    try:
                        retention_values = pd.to_numeric(integrated_retention[day1_cols[0]], errors='coerce')
                        avg_retention = retention_values.mean() * 100
                        if pd.isna(avg_retention):
                            avg_retention = 0
                    except:
                        avg_retention = 0
                
                st.markdown(f"""
                <div class="metric-weather">
                    <h3>{avg_retention:.1f}%</h3>
                    <p>平均次日留存</p>
                </div>
                """, unsafe_allow_html=True)
            
            # 留存可视化图表
            st.markdown("### 📊 留存分析图表")
            retention_viz_cols = st.columns(2, gap="large")
            
            with retention_viz_cols[0]:
                st.markdown('<div class="data-preview">', unsafe_allow_html=True)
                fig_retention = create_weather_visualization(integrated_retention, "📈 留存率趋势", "line")
                if fig_retention == "streamlit_chart":
                    pass  # 图表已经通过streamlit显示
                elif fig_retention:
                    st.pyplot(fig_retention, use_container_width=True)
                    plt.close(fig_retention)  # 释放内存
                st.markdown('</div>', unsafe_allow_html=True)
            
            with retention_viz_cols[1]:
                st.markdown('<div class="data-preview">', unsafe_allow_html=True)
                fig_retention_bar = create_weather_visualization(integrated_retention, "🔍 渠道留存对比", "bar")
                if fig_retention_bar == "streamlit_chart":
                    pass  # 图表已经通过streamlit显示
                elif fig_retention_bar:
                    st.pyplot(fig_retention_bar, use_container_width=True)
                    plt.close(fig_retention_bar)  # 释放内存
                st.markdown('</div>', unsafe_allow_html=True)
            
            # 留存数据预览
            st.markdown("### 📋 留存数据预览")
            st.markdown('<div class="weather-tabs">', unsafe_allow_html=True)
            retention_preview_tabs = st.tabs(["🎯 三端留存汇总"] + [f"🌧️ {ch.upper()}渠道" for ch in st.session_state.retention_results.keys()])
            st.markdown('</div>', unsafe_allow_html=True)
            
            with retention_preview_tabs[0]:
                st.markdown('<div class="data-preview">', unsafe_allow_html=True)
                st.dataframe(
                    integrated_retention.head(15), 
                    use_container_width=True,
                    hide_index=True
                )
                st.markdown('</div>', unsafe_allow_html=True)
            
            for i, (channel, df) in enumerate(st.session_state.retention_results.items()):
                with retention_preview_tabs[i + 1]:
                    st.markdown('<div class="data-preview">', unsafe_allow_html=True)
                    st.dataframe(
                        df.head(15), 
                        use_container_width=True,
                        hide_index=True
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # 留存数据下载
            st.markdown("### 💾 留存数据导出")
            retention_download_cols = st.columns([2, 1, 1, 1, 1])
            
            with retention_download_cols[0]:
                csv_data = integrated_retention.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下载三端留存汇总数据",
                    data=csv_data.encode('utf-8-sig'),
                    file_name=f"{today}_三端留存汇总.csv",
                    mime="text/csv",
                    type="primary",
                    key="retention_integrated"
                )
            
            # 分渠道下载
            for i, (channel, df) in enumerate(st.session_state.retention_results.items()):
                col_idx = (i + 1) % 4 + 1
                with retention_download_cols[col_idx]:
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"{channel.upper()}",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today}_留存_{channel}.csv",
                        mime="text/csv",
                        key=f"retention_{channel}"
                    )
    
    # 使用指南（在没有数据时显示）
    if not ('dau_results' in st.session_state and st.session_state.dau_results) and not ('retention_results' in st.session_state and st.session_state.retention_results):
        st.markdown("---")
        st.markdown("## 🌈 开始您的数据分析之旅")
        
        guide_cols = st.columns(3)
        
        with guide_cols[0]:
            st.markdown("""
            <div class="weather-card">
                <div class="weather-icon">📁</div>
                <h4>1. 上传数据文件</h4>
                <p style="color: #666;">
                将您的DAU和留存数据文件拖拽到对应的上传区域
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with guide_cols[1]:
            st.markdown("""
            <div class="weather-card">
                <div class="weather-icon">⚡</div>
                <h4>2. 智能数据处理</h4>
                <p style="color: #666;">
                系统自动识别格式，清洗数据，生成标准化报告
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with guide_cols[2]:
            st.markdown("""
            <div class="weather-card">
                <div class="weather-icon">📊</div>
                <h4>3. 洞察与导出</h4>
                <p style="color: #666;">
                查看可视化分析结果，导出处理后的数据文件
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # 功能说明（折叠显示）
    with st.expander("📚 平台功能详解", expanded=False):
        st.markdown("""
        ### 🎯 核心能力
        
        **📊 DAU数据智能分析**
        - 支持多渠道文件自动识别：MVP、Android、iOS
        - 智能数据清洗和标准化处理
        - 实时趋势分析和可视化图表生成
        - 异常数据检测和修复
        
        **🔄 留存数据深度分析**
        - 自动计算1-7日、14日、30日留存率
        - 多渠道留存表现对比分析
        - 用户行为模式识别和预测
        - 留存漏斗分析和优化建议
        
        **📈 可视化分析引擎**
        - 交互式图表生成：趋势线、柱状图、热力图
        - 多维度数据透视和钻取分析
        - 实时数据更新和动态展示
        - 自定义时间范围和指标筛选
        
        ### 📁 支持的文件格式
        
        **DAU数据文件**
        - 命名格式：`dau_渠道_日期.csv`
        - 示例：`dau_mvp_3.17.csv`, `dau_and_3.18.csv`, `dau_ios_3.19.csv`
        - 支持UTF-8和GBK编码格式
        
        **留存数据文件**
        - 命名格式：`retention_渠道.csv`
        - 示例：`retention_mvp.csv`, `retention_and.csv`, `retention_ios.csv`
        - 自动识别正式版和测试版数据
        
        ### 🚀 智能特性
        
        - **自动编码识别**：智能检测文件编码，确保中文内容正确显示
        - **数据类型推断**：自动识别数值、日期、文本等数据类型
        - **异常处理**：智能处理缺失值、异常值和格式错误
        - **内存优化**：高效的数据处理算法，支持大文件分析
        - **实时反馈**：处理进度实时显示，异常情况及时提醒
        
        ### 💡 使用建议
        
        1. **文件准备**：确保文件命名符合规范，数据格式标准
        2. **批量上传**：支持同时上传多个文件，系统自动识别和分类
        3. **结果验证**：查看生成的可视化图表，验证数据处理结果
        4. **定期分析**：建议定期使用本平台进行数据分析和监控
        """)
    
    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: white; padding: 3rem; background: rgba(255, 255, 255, 0.1); border-radius: 20px; backdrop-filter: blur(10px); margin: 2rem 0;'>
        <h3 style='margin: 0; font-family: Inter; font-weight: 600;'>🌤️ Weather Data Analytics</h3>
        <p style='margin: 0.5rem 0 0 0; opacity: 0.9; font-family: Inter;'>墨迹天气数据分析平台 | 让数据洞察如天气预报般精准</p>
        <small style='opacity: 0.7;'>智能分析 • 深度洞察 • 精准预测</small>
    </div>
    """, unsafe_allow_html=True)

# 初始化session state
if 'dau_results' not in st.session_state:
    st.session_state.dau_results = None
if 'retention_results' not in st.session_state:
    st.session_state.retention_results = None

if __name__ == "__main__":
    main()
