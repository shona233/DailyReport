import streamlit as st
import pandas as pd
import datetime
import re
import io
import zipfile
from typing import Dict, List, Optional

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

def process_uploaded_files(uploaded_files) -> Optional[Dict[str, pd.DataFrame]]:
    """处理上传的CSV文件"""
    
    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 存储每个渠道的DataFrame列表
    channel_dfs = {'mvp': [], 'and': [], 'ios': []}
    standard_columns = {'mvp': None, 'and': None, 'ios': None}
    
    processed_files = 0
    total_files = len(uploaded_files)
    
    # 创建详细日志容器
    log_container = st.expander("处理详情", expanded=False)
    
    for i, uploaded_file in enumerate(uploaded_files):
        try:
            # 更新进度
            progress = (i + 1) / total_files
            progress_bar.progress(progress)
            status_text.text(f"正在处理: {uploaded_file.name} ({i+1}/{total_files})")
            
            filename = uploaded_file.name
            
            # 检查文件名是否包含"dau"
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
                # 尝试不同的编码
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
            
            # 验证数据不为空
            if df.empty:
                log_container.warning(f"文件 {filename} 不包含数据，已跳过")
                continue
            
            # 删除指定的三列（如果存在）
            columns_to_drop = ['Total Conversions', 'Re-attribution', 'Re-engagement']
            original_cols = df.columns.tolist()
            df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')
            removed_cols = [col for col in columns_to_drop if col in original_cols]
            if removed_cols:
                log_container.info(f"已删除列: {', '.join(removed_cols)}")
            
            # 从文件名提取日期部分并格式化
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
            
            # 添加日期列到DataFrame的最前面
            df.insert(0, 'date', formatted_date)
            
            # 如果是iOS渠道且发现有问题的列
            if channel == 'ios' and 'Average eCPIUS$2.50' in df.columns:
                df = df.drop(columns=['Average eCPIUS$2.50'])
                log_container.info(f"移除iOS中的问题列: 'Average eCPIUS$2.50'")
            
            # 列标准化
            if standard_columns[channel] is None:
                standard_columns[channel] = df.columns.tolist()
                log_container.info(f"设置 {channel} 渠道的标准列")
            else:
                current_cols = df.columns.tolist()
                if current_cols != standard_columns[channel]:
                    # 调整列名以匹配标准列
                    missing_cols = [col for col in standard_columns[channel] if col not in current_cols]
                    extra_cols = [col for col in current_cols if col not in standard_columns[channel]]
                    
                    if missing_cols:
                        for col in missing_cols:
                            df[col] = 'N/A'
                        log_container.info(f"添加缺少的列: {', '.join(missing_cols)}")
                    
                    if extra_cols:
                        df = df.drop(columns=extra_cols)
                        log_container.info(f"移除多余的列: {', '.join(extra_cols)}")
                    
                    # 确保列顺序一致
                    df = df[standard_columns[channel]]
            
            # 将空值转换为"N/A"
            df = df.fillna('N/A')
            
            # 添加到对应渠道
            channel_dfs[channel].append(df)
            processed_files += 1
            
        except Exception as e:
            log_container.error(f"处理文件 {uploaded_file.name} 时发生错误: {str(e)}")
            continue
    
    # 完成进度
    progress_bar.progress(1.0)
    status_text.text(f"处理完成! 成功处理了 {processed_files} 个文件")
    
    if processed_files == 0:
        st.error("没有成功处理任何文件")
        return None
    
    # 合并数据并按日期排序
    merged_by_channel = {}
    
    for channel, df_list in channel_dfs.items():
        if df_list:
            st.info(f"正在合并渠道 {channel} 的 {len(df_list)} 个文件...")
            
            # 确保所有DataFrame都有相同的列
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
            
            # 合并该渠道的所有DataFrame
            merged_df = pd.concat(df_list, ignore_index=True)
            
            # 按日期排序
            try:
                merged_df['sort_key'] = merged_df['date'].apply(convert_date_to_sortable)
                merged_df = merged_df.sort_values(by='sort_key')
                merged_df = merged_df.drop(columns=['sort_key'])
            except Exception as e:
                st.warning(f"渠道 {channel} 排序时出错: {str(e)}")
            
            # 确保空值转换为N/A
            merged_df = merged_df.fillna('N/A')
            
            # iOS渠道特殊处理
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

def create_download_zip(merged_data: Dict[str, pd.DataFrame]) -> bytes:
    """创建包含所有合并文件的ZIP文件"""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        today = datetime.datetime.now().strftime("%m.%d")
        
        for channel, df in merged_data.items():
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_content = csv_buffer.getvalue().encode('utf-8')
            
            filename = f"{today} dau汇总_{channel}.csv"
            zip_file.writestr(filename, csv_content)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def main():
    st.set_page_config(
        page_title="CSV文件合并工具",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 CSV文件合并工具")
    st.markdown("---")
    
    # 说明文档
    with st.expander("📋 使用说明", expanded=True):
        st.markdown("""
        ### 功能说明
        - 合并多个DAU相关的CSV文件
        - 按渠道分组 (mvp, and, ios)
        - 自动处理日期格式和数据清洗
        - 生成按渠道分组的合并文件
        
        ### 文件命名要求
        - 文件名必须包含 "dau"
        - 文件名格式应为: `dau_渠道_日期.csv` (例如: `dau_mvp_3.17.csv`)
        - 支持的渠道: mvp, and, ios
        
        ### 数据处理
        - 自动删除 'Total Conversions', 'Re-attribution', 'Re-engagement' 列
        - 添加日期列并按日期排序
        - 统一列格式和处理缺失值
        """)
    
    # 文件上传
    st.subheader("📁 上传CSV文件")
    uploaded_files = st.file_uploader(
        "选择要合并的CSV文件",
        type=['csv'],
        accept_multiple_files=True,
        help="可以同时选择多个CSV文件"
    )
    
    if uploaded_files:
        st.success(f"已选择 {len(uploaded_files)} 个文件")
        
        # 显示上传的文件列表
        with st.expander("查看上传的文件"):
            for file in uploaded_files:
                st.text(f"📄 {file.name} ({file.size} bytes)")
        
        # 处理按钮
        if st.button("🚀 开始处理", type="primary"):
            with st.spinner("正在处理文件..."):
                merged_data = process_uploaded_files(uploaded_files)
            
            if merged_data:
                st.success("✅ 文件处理完成!")
                
                # 显示处理结果摘要
                st.subheader("📈 处理结果摘要")
                
                col1, col2, col3 = st.columns(3)
                
                for i, (channel, df) in enumerate(merged_data.items()):
                    with [col1, col2, col3][i]:
                        st.metric(
                            label=f"渠道 {channel.upper()}",
                            value=f"{len(df)} 行数据"
                        )
                        
                        # 显示日期范围
                        dates = sorted(df['date'].unique(), key=convert_date_to_sortable)
                        if dates:
                            st.text(f"日期范围: {dates[0]} ~ {dates[-1]}")
                
                # 数据预览
                st.subheader("👀 数据预览")
                
                tab_names = [f"渠道 {channel.upper()}" for channel in merged_data.keys()]
                tabs = st.tabs(tab_names)
                
                for tab, (channel, df) in zip(tabs, merged_data.items()):
                    with tab:
                        st.dataframe(df.head(10), use_container_width=True)
                        st.text(f"显示前10行，总共 {len(df)} 行")
                
                # 下载区域
                st.subheader("💾 下载合并后的文件")
                
                # 创建ZIP文件
                zip_data = create_download_zip(merged_data)
                today = datetime.datetime.now().strftime("%m.%d")
                
                st.download_button(
                    label="📦 下载所有合并文件 (ZIP)",
                    data=zip_data,
                    file_name=f"{today} dau汇总_所有渠道.zip",
                    mime="application/zip"
                )
                
                # 单独下载每个渠道的文件
                st.markdown("**或者单独下载各渠道文件:**")
                
                cols = st.columns(len(merged_data))
                for col, (channel, df) in zip(cols, merged_data.items()):
                    with col:
                        csv_data = df.to_csv(index=False, encoding='utf-8')
                        filename = f"{today} dau汇总_{channel}.csv"
                        
                        st.download_button(
                            label=f"📄 下载 {channel.upper()}",
                            data=csv_data.encode('utf-8'),
                            file_name=filename,
                            mime="text/csv"
                        )
    else:
        st.info("👆 请上传CSV文件开始处理")
    
    # 页脚
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>CSV文件合并工具 | 支持DAU数据处理和渠道分组</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
