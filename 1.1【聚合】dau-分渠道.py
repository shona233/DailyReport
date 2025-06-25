import streamlit as st
import pandas as pd
import datetime
import re
import io
from typing import Dict, List, Optional, Tuple

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
    
    log_container = st.expander("DAU文件处理详情", expanded=False)
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"正在处理: {uploaded_file.name} ({i+1}/{total_files})")
            
            filename = uploaded_file.name
            
            if "dau" not in filename.lower():
                log_container.warning(f"跳过文件 {filename}: 文件名不包含'dau'")
                continue
            
            # 从文件名中提取渠道信息
            if len(filename) > 7 and filename.startswith("dau_"):
                channel = filename[4:7]  # 获取渠道名 (mvp, and, ios)
                if channel not in channel_dfs:
                    log_container.warning(f"跳过文件 {filename}: 无法识别的渠道 '{channel}'")
                    continue
            else:
                log_container.warning(f"跳过文件 {filename}: 文件名格式不符合预期")
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
                
                log_container.success(f"成功读取 {filename}, 形状: {df.shape}")
                
            except Exception as e:
                log_container.error(f"读取文件 {filename} 失败: {str(e)}")
                continue
            
            if df.empty:
                log_container.warning(f"文件 {filename} 不包含数据，已跳过")
                continue
            
            # 删除指定的三列
            columns_to_drop = ['Total Conversions', 'Re-attribution', 'Re-engagement']
            original_cols = df.columns.tolist()
            df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')
            removed_cols = [col for col in columns_to_drop if col in original_cols]
            if removed_cols:
                log_container.info(f"已删除列: {', '.join(removed_cols)}")
            
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
                log_container.warning(f"无法从文件名 {filename} 提取日期，使用默认值")
            
            # 添加日期列
            df.insert(0, 'date', formatted_date)
            
            # iOS特殊处理
            if channel == 'ios' and 'Average eCPIUS$2.50' in df.columns:
                df = df.drop(columns=['Average eCPIUS$2.50'])
                log_container.info(f"移除iOS中的问题列")
            
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
            log_container.error(f"处理文件 {uploaded_file.name} 时发生错误: {str(e)}")
            continue
    
    progress_bar.progress(1.0)
    status_text.text(f"DAU文件处理完成! 成功处理了 {processed_files} 个文件")
    
    if processed_files == 0:
        st.error("没有成功处理任何DAU文件")
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
                st.warning(f"渠道 {channel} 排序时出错: {str(e)}")
            
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
    log_container = st.expander("留存文件处理详情", expanded=False)
    
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
                log_container.warning(f"跳过文件 {uploaded_file.name}: 无法识别的留存文件")
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
                    log_container.error(f"无法读取文件 {uploaded_file.name}")
                    continue
                
                log_container.success(f"成功读取 {uploaded_file.name}, 形状: {df.shape}")
                
            except Exception as e:
                log_container.error(f"读取文件 {uploaded_file.name} 失败: {str(e)}")
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
                    log_container.error(f"无法找到日期列")
                    continue
            
            # 排序数据
            try:
                df[date_column] = pd.to_datetime(df[date_column])
                df = df.sort_values(by=date_column)
            except:
                try:
                    df = df.sort_values(by=date_column)
                except:
                    log_container.warning(f"无法排序数据")
            
            # 检查用户列
            users_column = 'Users'
            if users_column not in df.columns:
                possible_users_columns = ['users', '用户数', 'DAU', 'User Count', 'user_count']
                for col in possible_users_columns:
                    if col in df.columns:
                        users_column = col
                        break
                
                if users_column not in df.columns:
                    log_container.error(f"无法找到用户列")
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
                else:
                    log_container.warning(f"无法计算 day{day} 留存率")
            
            processed_data[channel] = df
            log_container.success(f"成功处理 {channel} 渠道留存数据")
            
        except Exception as e:
            log_container.error(f"处理文件 {uploaded_file.name} 时发生错误: {str(e)}")
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
            st.warning(f"整合DAU数据排序时出错: {str(e)}")
        
        integrated_df = integrated_df.fillna('N/A')
        
        # 只保留前15列加三端列
        if len(integrated_df.columns) > 16:
            first_15_cols = integrated_df.iloc[:, :15].columns.tolist()
            if "三端" in integrated_df.columns and "三端" not in first_15_cols:
                cols_to_keep = first_15_cols + ["三端"]
                integrated_df = integrated_df[cols_to_keep]
        
        return integrated_df
        
    except Exception as e:
        st.error(f"整合DAU数据时出错: {str(e)}")
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
            st.warning(f"整合留存数据排序时出错: {str(e)}")
        
        integrated_df = integrated_df.fillna('N/A')
        
        return integrated_df
        
    except Exception as e:
        st.error(f"整合留存数据时出错: {str(e)}")
        return pd.DataFrame()

def main():
    st.set_page_config(
        page_title="完整数据处理工具",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 完整数据处理工具")
    st.markdown("**DAU合并 + 留存率计算 + 数据整合**")
    st.markdown("---")
    
    # 使用说明
    with st.expander("📋 使用说明", expanded=True):
        st.markdown("""
        ### 🎯 功能概述
        - **DAU文件合并**: 处理多个DAU CSV文件，按渠道分组合并
        - **留存率计算**: 处理留存数据文件，自动计算各天留存率
        - **数据整合**: 生成完整的三端数据文件和分渠道文件
        
        ### 📁 文件要求
        **DAU文件命名**: `dau_渠道_日期.csv` (例如: `dau_mvp_3.17.csv`)
        - 支持渠道: mvp, and, ios
        
        **留存文件命名**: 
        - `retention_ios.csv` (iOS渠道)
        - `retention_ios_formal.csv` (iOS正式渠道)
        - `retention_mvp.csv` (MVP渠道)
        - `retention_and.csv` (Android渠道)
        
        ### 📤 输出文件
        - **三端DAU汇总文件**: 包含所有渠道DAU数据
        - **三端留存汇总文件**: 包含所有渠道留存数据
        - **各渠道单独文件**: DAU和留存的分渠道文件
        """)
    
    # 创建两个标签页
    tab1, tab2 = st.tabs(["📈 DAU文件处理", "🔄 留存文件处理"])
    
    # 存储处理结果
    if 'dau_results' not in st.session_state:
        st.session_state.dau_results = None
    if 'retention_results' not in st.session_state:
        st.session_state.retention_results = None
    
    # DAU文件处理标签页
    with tab1:
        st.subheader("📁 上传DAU文件")
        dau_files = st.file_uploader(
            "选择DAU CSV文件",
            type=['csv'],
            accept_multiple_files=True,
            help="文件名格式: dau_渠道_日期.csv",
            key="dau_uploader"
        )
        
        if dau_files:
            st.success(f"已选择 {len(dau_files)} 个DAU文件")
            
            if st.button("🚀 处理DAU文件", type="primary", key="process_dau"):
                with st.spinner("正在处理DAU文件..."):
                    st.session_state.dau_results = process_dau_files(dau_files)
                
                if st.session_state.dau_results:
                    st.success("✅ DAU文件处理完成!")
    
    # 留存文件处理标签页
    with tab2:
        st.subheader("📁 上传留存文件")
        retention_files = st.file_uploader(
            "选择留存CSV文件",
            type=['csv'],
            accept_multiple_files=True,
            help="文件名格式: retention_渠道.csv",
            key="retention_uploader"
        )
        
        if retention_files:
            st.success(f"已选择 {len(retention_files)} 个留存文件")
            
            if st.button("🚀 处理留存文件", type="primary", key="process_retention"):
                with st.spinner("正在处理留存文件..."):
                    st.session_state.retention_results = process_retention_files(retention_files)
                
                if st.session_state.retention_results:
                    st.success("✅ 留存文件处理完成!")
    
    # 如果有处理结果，显示数据预览和下载选项
    if st.session_state.dau_results or st.session_state.retention_results:
        st.markdown("---")
        st.subheader("📊 处理结果")
        
        # 创建结果标签页
        result_tabs = []
        if st.session_state.dau_results:
            result_tabs.append("📈 DAU数据")
        if st.session_state.retention_results:
            result_tabs.append("🔄 留存数据")
        
        if result_tabs:
            tabs = st.tabs(result_tabs)
            tab_index = 0
            
            # DAU结果显示
            if st.session_state.dau_results:
                with tabs[tab_index]:
                    dau_data = st.session_state.dau_results
                    
                    # 创建整合的DAU数据
                    integrated_dau = create_integrated_dau(dau_data)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("处理渠道数", len(dau_data))
                    with col2:
                        total_rows = sum(len(df) for df in dau_data.values())
                        st.metric("总数据行数", total_rows)
                    with col3:
                        if not integrated_dau.empty:
                            st.metric("整合后行数", len(integrated_dau))
                    
                    # 数据预览
                    preview_tabs = st.tabs(["🎯 三端DAU汇总"] + [f"{ch.upper()}渠道" for ch in dau_data.keys()])
                    
                    # 三端汇总预览
                    with preview_tabs[0]:
                        if not integrated_dau.empty:
                            st.dataframe(integrated_dau.head(10), use_container_width=True)
                        else:
                            st.error("无法创建三端DAU汇总数据")
                    
                    # 各渠道预览
                    for i, (channel, df) in enumerate(dau_data.items()):
                        with preview_tabs[i + 1]:
                            st.dataframe(df.head(10), use_container_width=True)
                
                tab_index += 1
            
            # 留存结果显示
            if st.session_state.retention_results:
                with tabs[tab_index]:
                    retention_data = st.session_state.retention_results
                    
                    # 创建整合的留存数据
                    integrated_retention = create_integrated_retention(retention_data)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("处理渠道数", len(retention_data))
                    with col2:
                        total_rows = sum(len(df) for df in retention_data.values())
                        st.metric("总数据行数", total_rows)
                    with col3:
                        if not integrated_retention.empty:
                            st.metric("整合后行数", len(integrated_retention))
                    
                    # 数据预览
                    preview_tabs = st.tabs(["🎯 三端留存汇总"] + [f"{ch.upper()}渠道" for ch in retention_data.keys()])
                    
                    # 三端汇总预览
                    with preview_tabs[0]:
                        if not integrated_retention.empty:
                            st.dataframe(integrated_retention.head(10), use_container_width=True)
                        else:
                            st.error("无法创建三端留存汇总数据")
                    
                    # 各渠道预览
                    for i, (channel, df) in enumerate(retention_data.items()):
                        with preview_tabs[i + 1]:
                            st.dataframe(df.head(10), use_container_width=True)
        
        # 下载区域
        st.markdown("---")
        st.subheader("💾 下载处理后的文件")
        
        today = datetime.datetime.now().strftime("%m.%d")
        
        # 主要下载选项
        st.markdown("### 🎯 **汇总文件下载**")
        
        download_cols = st.columns(2)
        
        # DAU汇总下载
        if st.session_state.dau_results:
            with download_cols[0]:
                integrated_dau = create_integrated_dau(st.session_state.dau_results)
                if not integrated_dau.empty:
                    # 使用UTF-8 BOM编码确保中文正确显示
                    csv_data = integrated_dau.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📈 下载三端DAU汇总文件",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} 三端dau汇总.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    st.success(f"✅ {len(integrated_dau)} 行DAU数据")
                else:
                    st.error("❌ DAU汇总数据生成失败")
        
        # 留存汇总下载
        if st.session_state.retention_results:
            with download_cols[1]:
                integrated_retention = create_integrated_retention(st.session_state.retention_results)
                if not integrated_retention.empty:
                    # 使用UTF-8 BOM编码确保中文正确显示
                    csv_data = integrated_retention.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="🔄 下载三端留存汇总文件",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} 三端留存汇总.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    st.success(f"✅ {len(integrated_retention)} 行留存数据")
                else:
                    st.error("❌ 留存汇总数据生成失败")
        
        # 分渠道文件下载
        st.markdown("### 📁 **分渠道文件下载**")
        
        # DAU分渠道下载
        if st.session_state.dau_results:
            st.markdown("**DAU分渠道文件:**")
            dau_cols = st.columns(len(st.session_state.dau_results))
            for i, (channel, df) in enumerate(st.session_state.dau_results.items()):
                with dau_cols[i]:
                    # 使用UTF-8 BOM编码确保中文正确显示
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📈 DAU-{channel.upper()}",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} dau汇总_{channel}.csv",
                        mime="text/csv",
                        key=f"dau_{channel}"
                    )
                    st.text(f"{len(df)} 行数据")
        
        # 留存分渠道下载
        if st.session_state.retention_results:
            st.markdown("**留存分渠道文件:**")
            retention_cols = st.columns(len(st.session_state.retention_results))
            for i, (channel, df) in enumerate(st.session_state.retention_results.items()):
                with retention_cols[i]:
                    # 使用UTF-8 BOM编码确保中文正确显示
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"🔄 留存-{channel.upper()}",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} 留存_{channel}.csv",
                        mime="text/csv",
                        key=f"retention_{channel}"
                    )
                    st.text(f"{len(df)} 行数据")
    
    else:
        st.info("👆 请上传相应的文件开始处理")
    
    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>完整数据处理工具 | DAU合并 + 留存计算 + 数据整合</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
