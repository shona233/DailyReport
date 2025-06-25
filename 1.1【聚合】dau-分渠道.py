"""
完整数据处理工具 - 优化版
========================

环境要求:
- Python 3.8+
- streamlit >= 1.28.0
- pandas >= 1.5.0
- numpy >= 1.20.0
- openpyxl >= 3.0.0
- plotly >= 5.0.0

安装命令: pip install streamlit pandas numpy openpyxl plotly
"""

import streamlit as st
import pandas as pd
import datetime
import re
import io
import numpy as np
import warnings
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Tuple

# 忽略警告
warnings.filterwarnings('ignore')

# 页面配置
st.set_page_config(
    page_title="智能数据处理平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem 0;
    }
    .success-message {
        background: linear-gradient(90deg, #56ab2f 0%, #a8e6cf 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin: 1rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f0f2f6;
        border-radius: 8px 8px 0 0;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
    }
</style>
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

def create_data_visualization(df, title, chart_type="line"):
    """创建数据可视化图表"""
    try:
        # 检查数据是否为空
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
        
        # 创建图表
        if chart_type == "line":
            # 寻找数值列
            numeric_cols = df_viz.select_dtypes(include=[np.number]).columns.tolist()
            
            if len(numeric_cols) > 0:
                fig = go.Figure()
                
                # 添加多个数值列的线图
                for col in numeric_cols[:5]:  # 最多显示5条线
                    fig.add_trace(go.Scatter(
                        x=df_viz[date_col],
                        y=df_viz[col],
                        mode='lines+markers',
                        name=col,
                        line=dict(width=2)
                    ))
                
                fig.update_layout(
                    title=title,
                    xaxis_title="日期",
                    yaxis_title="数值",
                    hovermode='x unified',
                    height=400,
                    template="plotly_white"
                )
                
                return fig
                
        elif chart_type == "bar":
            # 创建柱状图
            if '三端' in df_viz.columns:
                # 按渠道分组统计
                numeric_cols = df_viz.select_dtypes(include=[np.number]).columns.tolist()
                if numeric_cols:
                    agg_data = df_viz.groupby('三端')[numeric_cols[0]].sum().reset_index()
                    
                    fig = px.bar(
                        agg_data,
                        x='三端',
                        y=numeric_cols[0],
                        title=title,
                        color='三端',
                        template="plotly_white"
                    )
                    
                    fig.update_layout(height=400)
                    return fig
        
        elif chart_type == "heatmap":
            # 创建热力图（如果有足够的数值数据）
            numeric_cols = df_viz.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) >= 2:
                corr_matrix = df_viz[numeric_cols].corr()
                
                fig = px.imshow(
                    corr_matrix,
                    title=f"{title} - 相关性热力图",
                    color_continuous_scale="RdBu_r",
                    aspect="auto"
                )
                
                fig.update_layout(height=400)
                return fig
                
    except Exception as e:
        st.warning(f"图表创建失败: {str(e)}")
        return None
    
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
            status_text.text(f"正在处理: {uploaded_file.name} ({i+1}/{total_files})")
            
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
    status_text.text(f"DAU文件处理完成! 成功处理了 {processed_files} 个文件")
    
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
            status_text.text(f"正在处理: {uploaded_file.name} ({i+1}/{total_files})")
            
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
    status_text.text(f"留存文件处理完成! 成功处理了 {len(processed_data)} 个文件")
    
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
    # 主标题
    st.markdown("""
    <div class="main-header">
        <h1>🚀 智能数据处理平台</h1>
        <p>DAU合并 • 留存计算 • 数据可视化 • 一站式解决方案</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 核心功能区域
    st.markdown("## 🎯 核心功能")
    
    # 创建两列布局
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>📈 DAU数据处理</h3>
            <p>• 自动识别渠道文件<br>
            • 智能数据合并<br>
            • 实时可视化分析</p>
        </div>
        """, unsafe_allow_html=True)
        
        # DAU文件上传
        dau_files = st.file_uploader(
            "拖入DAU文件 (支持多选)",
            type=['csv'],
            accept_multiple_files=True,
            help="文件格式: dau_渠道_日期.csv",
            key="dau_uploader"
        )
        
        if dau_files:
            st.success(f"✅ 已选择 {len(dau_files)} 个DAU文件")
            
            if st.button("🚀 开始处理DAU数据", type="primary", key="process_dau"):
                with st.spinner("🔄 智能处理中..."):
                    st.session_state.dau_results = process_dau_files(dau_files)
                
                if st.session_state.dau_results:
                    st.markdown("""
                    <div class="success-message">
                        ✨ DAU数据处理完成！已生成可视化图表和分析报告
                    </div>
                    """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>🔄 留存数据处理</h3>
            <p>• 自动计算留存率<br>
            • 多渠道数据整合<br>
            • 趋势分析可视化</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 留存文件上传
        retention_files = st.file_uploader(
            "拖入留存文件 (支持多选)",
            type=['csv'],
            accept_multiple_files=True,
            help="文件格式: retention_渠道.csv",
            key="retention_uploader"
        )
        
        if retention_files:
            st.success(f"✅ 已选择 {len(retention_files)} 个留存文件")
            
            if st.button("🚀 开始处理留存数据", type="primary", key="process_retention"):
                with st.spinner("🔄 智能处理中..."):
                    st.session_state.retention_results = process_retention_files(retention_files)
                
                if st.session_state.retention_results:
                    st.markdown("""
                    <div class="success-message">
                        ✨ 留存数据处理完成！已生成留存率分析和趋势图表
                    </div>
                    """, unsafe_allow_html=True)
    
    # 数据可视化和结果展示
    if 'dau_results' in st.session_state and st.session_state.dau_results:
        st.markdown("---")
        st.markdown("## 📊 DAU数据分析")
        
        # 创建整合数据
        integrated_dau = create_integrated_dau(st.session_state.dau_results)
        
        if not integrated_dau.empty:
            # 数据统计卡片
            metric_cols = st.columns(4)
            with metric_cols[0]:
                st.markdown("""
                <div class="metric-card">
                    <h3>{}</h3>
                    <p>处理渠道数</p>
                </div>
                """.format(len(st.session_state.dau_results)), unsafe_allow_html=True)
            
            with metric_cols[1]:
                total_rows = sum(len(df) for df in st.session_state.dau_results.values())
                st.markdown("""
                <div class="metric-card">
                    <h3>{}</h3>
                    <p>总数据行数</p>
                </div>
                """.format(total_rows), unsafe_allow_html=True)
            
            with metric_cols[2]:
                st.markdown("""
                <div class="metric-card">
                    <h3>{}</h3>
                    <p>整合后行数</p>
                </div>
                """.format(len(integrated_dau)), unsafe_allow_html=True)
            
            with metric_cols[3]:
                if 'Installs' in integrated_dau.columns:
                    total_installs = integrated_dau['Installs'].replace('N/A', 0).astype(str).str.replace(',', '').astype(float).sum()
                    st.markdown("""
                    <div class="metric-card">
                        <h3>{:,.0f}</h3>
                        <p>总安装量</p>
                    </div>
                    """.format(total_installs), unsafe_allow_html=True)
            
            # 可视化图表
            viz_cols = st.columns(2)
            
            with viz_cols[0]:
                # 趋势图
                fig_line = create_data_visualization(integrated_dau, "DAU数据趋势分析", "line")
                if fig_line:
                    st.plotly_chart(fig_line, use_container_width=True)
            
            with viz_cols[1]:
                # 渠道对比图
                fig_bar = create_data_visualization(integrated_dau, "渠道数据对比", "bar")
                if fig_bar:
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            # 数据预览
            st.markdown("### 📋 数据预览")
            preview_tabs = st.tabs(["🎯 三端DAU汇总"] + [f"{ch.upper()}渠道" for ch in st.session_state.dau_results.keys()])
            
            with preview_tabs[0]:
                st.dataframe(integrated_dau.head(15), use_container_width=True)
            
            for i, (channel, df) in enumerate(st.session_state.dau_results.items()):
                with preview_tabs[i + 1]:
                    st.dataframe(df.head(15), use_container_width=True)
            
            # 下载按钮
            st.markdown("### 💾 下载数据")
            download_cols = st.columns(3)
            
            today = datetime.datetime.now().strftime("%m.%d")
            
            with download_cols[0]:
                csv_data = integrated_dau.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下载三端DAU汇总",
                    data=csv_data.encode('utf-8-sig'),
                    file_name=f"{today} 三端dau汇总.csv",
                    mime="text/csv",
                    type="primary"
                )
            
            # 分渠道下载
            for i, (channel, df) in enumerate(st.session_state.dau_results.items()):
                col_idx = (i + 1) % 3
                with download_cols[col_idx]:
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 {channel.upper()}渠道",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} dau_{channel}.csv",
                        mime="text/csv",
                        key=f"dau_{channel}"
                    )
    
    # 留存数据可视化
    if 'retention_results' in st.session_state and st.session_state.retention_results:
        st.markdown("---")
        st.markdown("## 🔄 留存数据分析")
        
        # 创建整合数据
        integrated_retention = create_integrated_retention(st.session_state.retention_results)
        
        if not integrated_retention.empty:
            # 留存率趋势图
            retention_viz_cols = st.columns(2)
            
            with retention_viz_cols[0]:
                # 留存率趋势
                fig_retention = create_data_visualization(integrated_retention, "留存率趋势分析", "line")
                if fig_retention:
                    st.plotly_chart(fig_retention, use_container_width=True)
            
            with retention_viz_cols[1]:
                # 渠道留存对比
                fig_retention_bar = create_data_visualization(integrated_retention, "渠道留存对比", "bar")
                if fig_retention_bar:
                    st.plotly_chart(fig_retention_bar, use_container_width=True)
            
            # 留存数据预览
            st.markdown("### 📋 留存数据预览")
            retention_preview_tabs = st.tabs(["🎯 三端留存汇总"] + [f"{ch.upper()}渠道" for ch in st.session_state.retention_results.keys()])
            
            with retention_preview_tabs[0]:
                st.dataframe(integrated_retention.head(15), use_container_width=True)
            
            for i, (channel, df) in enumerate(st.session_state.retention_results.items()):
                with retention_preview_tabs[i + 1]:
                    st.dataframe(df.head(15), use_container_width=True)
            
            # 留存数据下载
            st.markdown("### 💾 下载留存数据")
            retention_download_cols = st.columns(3)
            
            with retention_download_cols[0]:
                csv_data = integrated_retention.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 下载三端留存汇总",
                    data=csv_data.encode('utf-8-sig'),
                    file_name=f"{today} 三端留存汇总.csv",
                    mime="text/csv",
                    type="primary",
                    key="retention_integrated"
                )
            
            # 分渠道下载
            for i, (channel, df) in enumerate(st.session_state.retention_results.items()):
                col_idx = (i + 1) % 3
                with retention_download_cols[col_idx]:
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 {channel.upper()}留存",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} 留存_{channel}.csv",
                        mime="text/csv",
                        key=f"retention_{channel}"
                    )
    
    # 高级功能区域
    if not ('dau_results' in st.session_state and st.session_state.dau_results) and not ('retention_results' in st.session_state and st.session_state.retention_results):
        st.markdown("---")
        st.markdown("## 🎯 开始使用")
        st.info("👆 请在上方拖入您的数据文件开始处理，系统将自动生成可视化分析报告")
    
    # 功能说明（折叠显示）
    with st.expander("📋 详细功能说明", expanded=False):
        st.markdown("""
        ### 🎯 核心功能
        
        **📈 DAU数据处理**
        - 自动识别文件格式：`dau_渠道_日期.csv`
        - 支持渠道：MVP、Android、iOS
        - 智能数据清洗和标准化
        - 自动生成趋势分析图表
        
        **🔄 留存数据处理**
        - 自动计算1-7日、14日、30日留存率
        - 支持多渠道数据整合
        - 生成留存率趋势可视化
        - 渠道间对比分析
        
        **📊 数据可视化**
        - 实时生成交互式图表
        - 多维度数据分析
        - 趋势预测和洞察
        - 支持数据导出
        
        ### 📁 文件格式要求
        
        **DAU文件**：`dau_mvp_3.17.csv`、`dau_and_3.18.csv`、`dau_ios_3.19.csv`
        
        **留存文件**：`retention_mvp.csv`、`retention_and.csv`、`retention_ios.csv`
        
        ### 🚀 快速开始
        1. 拖入文件到对应上传区域
        2. 点击"开始处理"按钮
        3. 查看自动生成的可视化分析
        4. 下载处理后的数据文件
        
        ### 💡 技术特性
        - 智能编码识别，支持中文文件
        - 自动数据类型推断
        - 异常数据处理和修复
        - 高性能数据处理引擎
        """)
    
    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p><strong>🚀 智能数据处理平台</strong> | 让数据分析更简单高效</p>
        <small>支持DAU合并 • 留存计算 • 数据可视化 • 一键导出</small>
    </div>
    """, unsafe_allow_html=True)

# 初始化session state
if 'dau_results' not in st.session_state:
    st.session_state.dau_results = None
if 'retention_results' not in st.session_state:
    st.session_state.retention_results = None

if __name__ == "__main__":
    main()
