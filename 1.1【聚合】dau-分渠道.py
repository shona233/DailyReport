"""
日报数据处理工具 - 优化版
========================

环境要求:
- Python 3.8+
- streamlit >= 1.28.0
- pandas >= 1.5.0
- numpy >= 1.20.0
- openpyxl >= 3.0.0

安装命令:
pip install streamlit pandas numpy openpyxl

运行命令:
streamlit run app.py
"""

import streamlit as st
import pandas as pd
import datetime
import re
import io
import numpy as np
import warnings
from typing import Dict, List, Optional, Tuple

# 忽略警告
warnings.filterwarnings('ignore')

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

def delete_excel_by_date_interface():
    """底表日期删除界面"""
    st.subheader("底表日期删除功能")
    
    # 上传Excel文件
    uploaded_excel = st.file_uploader(
        "上传底表Excel文件",
        type=['xlsx'],
        help="请上传需要删除日期的Excel底表文件",
        key="excel_uploader"
    )
    
    if uploaded_excel:
        st.success(f"已上传文件: {uploaded_excel.name}")
        
        # 计算默认日期（今天-2天）
        from datetime import datetime, timedelta
        default_date = datetime.now() - timedelta(days=2)
        default_date_mmdd = default_date.strftime("%m%d")
        default_date_display = default_date.strftime("%Y/%m/%d")
        
        st.info(f"默认截止日期（今天-2天）: {default_date_display}")
        
        # 创建两列输入
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**三端DAU截止日期**")
            dau_date = st.text_input(
                "格式: MMDD (如: 0601)",
                value=default_date_mmdd,
                help="删除该日期及之后的所有DAU数据",
                key="dau_date"
            )
        
        with col2:
            st.markdown("**三端留存截止日期**")
            retention_date = st.text_input(
                "格式: MMDD (如: 0601)",
                value="",
                help="删除该日期及之后的所有留存数据",
                key="retention_date"
            )
        
        if st.button("执行删除操作", type="primary"):
            if not retention_date:
                st.error("请输入三端留存截止日期")
                return
            
            try:
                # 验证日期格式
                for date_input, name in [(dau_date, "DAU"), (retention_date, "留存")]:
                    if len(date_input) != 4 or not date_input.isdigit():
                        st.error(f"{name}日期格式错误，请输入4位数字")
                        return
                
                # 转换日期格式
                dau_month, dau_day = dau_date[:2], dau_date[2:]
                ret_month, ret_day = retention_date[:2], retention_date[2:]
                
                dau_cutoff = f"2025/{dau_month}/{dau_day}"
                ret_cutoff = f"2025/{ret_month}/{ret_day}"
                
                # 验证日期有效性
                pd.to_datetime(dau_cutoff)
                pd.to_datetime(ret_cutoff)
                
                st.info(f"将删除:\n- 三端DAU: {dau_cutoff} 及之后的数据\n- 三端留存: {ret_cutoff} 及之后的数据")
                
                with st.spinner("正在处理Excel文件..."):
                    # 读取Excel文件
                    excel_content = uploaded_excel.getvalue()
                    excel_file = pd.ExcelFile(io.BytesIO(excel_content))
                    
                    all_sheets_data = {}
                    target_sheets = ['三端留存', '三端DAU']
                    
                    for sheet_name in excel_file.sheet_names:
                        try:
                            df = pd.read_excel(io.BytesIO(excel_content), sheet_name=sheet_name)
                            
                            if sheet_name not in target_sheets:
                                all_sheets_data[sheet_name] = df
                                continue
                            
                            # 获取截止日期
                            cutoff_date_str = dau_cutoff if sheet_name == '三端DAU' else ret_cutoff
                            
                            if len(df) == 0:
                                all_sheets_data[sheet_name] = df
                                continue
                            
                            # 获取第一列作为日期列
                            date_column = df.columns[0]
                            
                            # 过滤有效数据
                            df_filtered = df.dropna(subset=[date_column]).copy()
                            
                            if len(df_filtered) == 0:
                                all_sheets_data[sheet_name] = pd.DataFrame()
                                continue
                            
                            # 转换日期
                            df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce')
                            df_filtered = df_filtered.dropna(subset=[date_column]).copy()
                            
                            if len(df_filtered) == 0:
                                all_sheets_data[sheet_name] = pd.DataFrame()
                                continue
                            
                            # 转换为字符串格式进行比较
                            df_filtered[date_column] = df_filtered[date_column].dt.strftime('%Y/%m/%d')
                            
                            # 删除指定日期及之后的数据
                            df_final = df_filtered[df_filtered[date_column] < cutoff_date_str].copy()
                            all_sheets_data[sheet_name] = df_final
                            
                        except Exception as e:
                            st.error(f"处理sheet '{sheet_name}' 时出错: {str(e)}")
                            all_sheets_data[sheet_name] = pd.DataFrame()
                    
                    # 创建新的Excel文件
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        for sheet_name, data in all_sheets_data.items():
                            data.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    output.seek(0)
                    
                    st.success("删除操作完成!")
                    
                    # 显示删除结果统计
                    st.markdown("### 删除结果统计")
                    for sheet_name in target_sheets:
                        if sheet_name in all_sheets_data:
                            data = all_sheets_data[sheet_name]
                            cutoff_used = dau_cutoff if sheet_name == '三端DAU' else ret_cutoff
                            if len(data) > 0:
                                date_col = data.columns[0]
                                min_date = data[date_col].min()
                                max_date = data[date_col].max()
                                st.write(f"**{sheet_name}**: {len(data)}行 (截止: {cutoff_used}, 日期区间: {min_date} 至 {max_date})")
                            else:
                                st.write(f"**{sheet_name}**: 0行 (截止: {cutoff_used})")
                    
                    # 提供下载
                    st.download_button(
                        label="下载处理后的Excel文件",
                        data=output.getvalue(),
                        file_name=f"底表_删除后_{datetime.now().strftime('%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
            except Exception as e:
                st.error(f"处理过程中发生错误: {str(e)}")

def validate_data_interface():
    """数据校验界面"""
    st.subheader("数据校验功能")
    
    # 上传文件
    col1, col2 = st.columns(2)
    
    with col1:
        excel_file = st.file_uploader(
            "上传底表Excel文件",
            type=['xlsx'],
            help="包含三端DAU和三端留存数据的Excel文件",
            key="validate_excel"
        )
    
    with col2:
        csv_file = st.file_uploader(
            "上传retention_all.csv文件",
            type=['csv'],
            help="用于对比校验的retention_all.csv文件",
            key="validate_csv"
        )
    
    if excel_file and csv_file:
        if st.button("开始数据校验", type="primary"):
            with st.spinner("正在进行数据校验..."):
                try:
                    # 读取Excel文件
                    excel_content = excel_file.getvalue()
                    
                    # 读取三端DAU数据
                    dau_df = pd.read_excel(io.BytesIO(excel_content), sheet_name='三端DAU')
                    
                    # 读取三端留存数据
                    retention_df = pd.read_excel(io.BytesIO(excel_content), sheet_name='三端留存')
                    
                    # 读取CSV文件
                    csv_content = csv_file.getvalue()
                    retention_all_df = pd.read_csv(io.StringIO(csv_content.decode('utf-8')))
                    
                    # 处理retention_all数据
                    def map_app_id_to_platform(app_id):
                        if app_id == 'com.weather.mjweather':
                            return 'android'
                        elif app_id == 'id6720731790':
                            return 'ios'
                        elif app_id == 'com.moji.international':
                            return 'mvp'
                        else:
                            return 'unknown'
                    
                    # 寻找App Id列
                    app_id_columns = ['App Id', 'app_id', 'AppId', 'app id']
                    app_id_col = None
                    for col in app_id_columns:
                        if col in retention_all_df.columns:
                            app_id_col = col
                            break
                    
                    if app_id_col:
                        retention_all_df['三端'] = retention_all_df[app_id_col].apply(map_app_id_to_platform)
                    
                    # 创建数据透视表
                    st.markdown("### 数据透视表分析")
                    
                    # DAU透视表
                    if not dau_df.empty:
                        date_col = dau_df.columns[0]
                        if '三端' in dau_df.columns and 'Installs' in dau_df.columns:
                            dau_df[date_col] = pd.to_datetime(dau_df[date_col])
                            dau_pivot = pd.pivot_table(
                                dau_df,
                                values='Installs',
                                index=date_col,
                                columns='三端',
                                aggfunc='sum',
                                fill_value=0
                            ).sort_index(ascending=False).astype(int)
                            
                            st.markdown("**DAU数据透视表 (前10行)**")
                            st.dataframe(dau_pivot.head(10))
                    
                    # 留存透视表
                    if not retention_df.empty:
                        date_col = retention_df.columns[0]
                        if '三端' in retention_df.columns and 'Users' in retention_df.columns:
                            retention_df[date_col] = pd.to_datetime(retention_df[date_col])
                            retention_pivot = pd.pivot_table(
                                retention_df,
                                values='Users',
                                index=date_col,
                                columns='三端',
                                aggfunc='sum',
                                fill_value=0
                            ).sort_index(ascending=False).astype(int)
                            
                            st.markdown("**留存数据透视表 (前10行)**")
                            st.dataframe(retention_pivot.head(10))
                    
                    # retention_all透视表
                    if not retention_all_df.empty and app_id_col:
                        cohort_col = 'Cohort Day'
                        if cohort_col in retention_all_df.columns:
                            # 寻找数值列
                            exclude_cols = [cohort_col, app_id_col, '三端']
                            numeric_cols = [col for col in retention_all_df.columns 
                                          if col not in exclude_cols and pd.api.types.is_numeric_dtype(retention_all_df[col])]
                            
                            if numeric_cols:
                                value_col = numeric_cols[0]
                                retention_all_df[cohort_col] = pd.to_datetime(retention_all_df[cohort_col])
                                retention_all_pivot = pd.pivot_table(
                                    retention_all_df,
                                    values=value_col,
                                    index=cohort_col,
                                    columns='三端',
                                    aggfunc='sum',
                                    fill_value=0
                                ).sort_index(ascending=False).astype(int)
                                
                                st.markdown("**Retention_all数据透视表 (前10行)**")
                                st.dataframe(retention_all_pivot.head(10))
                                
                                # 数值对比分析
                                if 'retention_pivot' in locals():
                                    st.markdown("### 数值对比分析")
                                    
                                    overlapping_dates = set(retention_pivot.index).intersection(set(retention_all_pivot.index))
                                    
                                    if overlapping_dates:
                                        comparison_data = []
                                        
                                        for date in sorted(overlapping_dates, reverse=True)[:10]:  # 显示最近10天
                                            retention_sum = retention_pivot.loc[date].sum()
                                            retention_all_sum = retention_all_pivot.loc[date].sum()
                                            
                                            if retention_all_sum > 0:
                                                difference = retention_sum - retention_all_sum
                                                percentage = (difference / retention_all_sum * 100) if retention_all_sum != 0 else 0
                                                
                                                comparison_data.append({
                                                    '日期': date.strftime('%Y-%m-%d'),
                                                    '留存总和': retention_sum,
                                                    'Retention_all总和': retention_all_sum,
                                                    '差异': difference,
                                                    '差异百分比': f"{percentage:.2f}%"
                                                })
                                        
                                        if comparison_data:
                                            comparison_df = pd.DataFrame(comparison_data)
                                            st.dataframe(comparison_df)
                                            
                                            # 统计摘要
                                            differences = [row['差异'] for row in comparison_data]
                                            if differences:
                                                st.markdown("**对比摘要:**")
                                                st.write(f"- 平均差异: {np.mean(differences):.0f}")
                                                st.write(f"- 最大差异: {max(differences):.0f}")
                                                st.write(f"- 最小差异: {min(differences):.0f}")
                    
                    st.success("数据校验完成!")
                    
                except Exception as e:
                    st.error(f"数据校验过程中发生错误: {str(e)}")

def main():
    st.set_page_config(
        page_title="日报数据处理平台",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 自定义CSS样式
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 0;
        margin: -1rem -1rem 2rem -1rem;
        border-radius: 0 0 10px 10px;
    }
    .main-title {
        color: white;
        text-align: center;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .main-subtitle {
        color: rgba(255,255,255,0.9);
        text-align: center;
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        font-weight: 300;
    }
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    .metric-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 主标题区域
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">日报数据处理平台</h1>
        <p class="main-subtitle">DAU合并 • 留存率计算 • 底表管理 • 数据校验</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 创建四个标签页
    tab1, tab2, tab3, tab4 = st.tabs(["DAU文件处理", "留存文件处理", "底表日期删除", "数据校验"])
    
    # 存储处理结果
    if 'dau_results' not in st.session_state:
        st.session_state.dau_results = None
    if 'retention_results' not in st.session_state:
        st.session_state.retention_results = None
    
    # DAU文件处理标签页
    with tab1:
        st.subheader("DAU文件处理")
        st.markdown("上传DAU CSV文件进行批量处理和合并")
        
        dau_files = st.file_uploader(
            "选择DAU CSV文件",
            type=['csv'],
            accept_multiple_files=True,
            help="文件名格式: dau_渠道_日期.csv",
            key="dau_uploader"
        )
        
        if dau_files:
            st.success(f"已选择 {len(dau_files)} 个DAU文件")
            
            if st.button("处理DAU文件", type="primary", key="process_dau"):
                with st.spinner("正在处理DAU文件..."):
                    st.session_state.dau_results = process_dau_files(dau_files)
                
                if st.session_state.dau_results:
                    st.success("DAU文件处理完成!")
    
    # 留存文件处理标签页
    with tab2:
        st.subheader("留存文件处理")
        st.markdown("上传留存CSV文件进行处理和留存率计算")
        
        retention_files = st.file_uploader(
            "选择留存CSV文件",
            type=['csv'],
            accept_multiple_files=True,
            help="文件名格式: retention_渠道.csv",
            key="retention_uploader"
        )
        
        if retention_files:
            st.success(f"已选择 {len(retention_files)} 个留存文件")
            
            if st.button("处理留存文件", type="primary", key="process_retention"):
                with st.spinner("正在处理留存文件..."):
                    st.session_state.retention_results = process_retention_files(retention_files)
                
                if st.session_state.retention_results:
                    st.success("留存文件处理完成!")
    
    # 底表日期删除标签页
    with tab3:
        delete_excel_by_date_interface()
    
    # 数据校验标签页
    with tab4:
        validate_data_interface()
    
    # 如果有DAU或留存处理结果，显示数据预览和下载选项
    if st.session_state.dau_results or st.session_state.retention_results:
        st.markdown("---")
        st.subheader("处理结果")
        
        # 创建结果标签页
        result_tabs = []
        if st.session_state.dau_results:
            result_tabs.append("DAU数据")
        if st.session_state.retention_results:
            result_tabs.append("留存数据")
        
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
                    preview_tabs = st.tabs(["三端DAU汇总"] + [f"{ch.upper()}渠道" for ch in dau_data.keys()])
                    
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
                    preview_tabs = st.tabs(["三端留存汇总"] + [f"{ch.upper()}渠道" for ch in retention_data.keys()])
                    
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
        st.subheader("文件下载")
        
        today = datetime.datetime.now().strftime("%m.%d")
        
        # 主要下载选项
        st.markdown("### 汇总文件")
        
        download_cols = st.columns(2)
        
        # DAU汇总下载
        if st.session_state.dau_results:
            with download_cols[0]:
                integrated_dau = create_integrated_dau(st.session_state.dau_results)
                if not integrated_dau.empty:
                    # 使用UTF-8 BOM编码确保中文正确显示
                    csv_data = integrated_dau.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载三端DAU汇总文件",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} 三端dau汇总.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    st.success(f"✓ {len(integrated_dau)} 行DAU数据")
                else:
                    st.error("✗ DAU汇总数据生成失败")
        
        # 留存汇总下载
        if st.session_state.retention_results:
            with download_cols[1]:
                integrated_retention = create_integrated_retention(st.session_state.retention_results)
                if not integrated_retention.empty:
                    # 使用UTF-8 BOM编码确保中文正确显示
                    csv_data = integrated_retention.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载三端留存汇总文件",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} 三端留存汇总.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    st.success(f"✓ {len(integrated_retention)} 行留存数据")
                else:
                    st.error("✗ 留存汇总数据生成失败")
        
        # 分渠道文件下载
        st.markdown("### 分渠道文件")
        
        # DAU分渠道下载
        if st.session_state.dau_results:
            st.markdown("**DAU分渠道文件:**")
            dau_cols = st.columns(len(st.session_state.dau_results))
            for i, (channel, df) in enumerate(st.session_state.dau_results.items()):
                with dau_cols[i]:
                    # 使用UTF-8 BOM编码确保中文正确显示
                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"DAU-{channel.upper()}",
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
                        label=f"留存-{channel.upper()}",
                        data=csv_data.encode('utf-8-sig'),
                        file_name=f"{today} 留存_{channel}.csv",
                        mime="text/csv",
                        key=f"retention_{channel}"
                    )
                    st.text(f"{len(df)} 行数据")
    
    else:
        # 显示功能介绍
        st.markdown("### 平台功能")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <h4>DAU文件处理</h4>
                <p>• 批量处理多个DAU CSV文件</p>
                <p>• 自动按渠道分组合并</p>
                <p>• 统一数据格式和日期</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="feature-card">
                <h4>底表日期删除</h4>
                <p>• 删除Excel底表指定日期后的数据</p>
                <p>• 支持分别设置DAU和留存截止日期</p>
                <p>• 自动生成处理结果统计</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <h4>留存文件处理</h4>
                <p>• 处理多渠道留存数据文件</p>
                <p>• 自动计算各天留存率</p>
                <p>• 支持iOS、Android、MVP渠道</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="feature-card">
                <h4>数据校验</h4>
                <p>• 对比底表与retention_all数据</p>
                <p>• 生成数据透视表分析</p>
                <p>• 提供详细的差异报告</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 使用说明
    with st.expander("使用说明", expanded=False):
        st.markdown("""
        ### 功能概述
        1. **DAU文件合并**: 处理多个DAU CSV文件，按渠道分组合并
        2. **留存率计算**: 处理留存数据文件，自动计算各天留存率
        3. **底表日期删除**: 删除Excel底表中指定日期及之后的数据
        4. **数据校验**: 对比分析底表数据与retention_all.csv数据的一致性
        
        ### 文件要求
        **DAU文件命名**: `dau_渠道_日期.csv` (例如: `dau_mvp_3.17.csv`)
        - 支持渠道: mvp, and, ios
        
        **留存文件命名**: 
        - `retention_ios.csv` (iOS渠道)
        - `retention_ios_formal.csv` (iOS正式渠道)
        - `retention_mvp.csv` (MVP渠道)
        - `retention_and.csv` (Android渠道)
        
        **底表文件**: Excel格式，包含"三端DAU"和"三端留存"工作表
        
        ### 输出文件
        - **三端DAU汇总文件**: 包含所有渠道DAU数据
        - **三端留存汇总文件**: 包含所有渠道留存数据
        - **各渠道单独文件**: DAU和留存的分渠道文件
        - **处理后底表**: 删除指定日期后的Excel文件
        - **数据校验报告**: 数据一致性分析结果
        """)
    
    # 页脚信息
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 20px;'>
            <h4>日报数据处理平台</h4>
            <p><strong>环境要求:</strong> Python 3.8+ | streamlit | pandas | numpy | openpyxl</p>
            <p style='margin-top: 15px; font-size: 14px; background-color: #f8f9fa; padding: 10px; border-radius: 5px;'>
                <strong>安装依赖:</strong> 
                <code style='background-color: #e9ecef; padding: 2px 6px; border-radius: 3px; color: #495057;'>
                pip install streamlit pandas numpy openpyxl
                </code>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
