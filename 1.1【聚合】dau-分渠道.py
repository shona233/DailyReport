import pandas as pd
import os
import glob
import datetime
import sys
import re
from openpyxl import load_workbook


def merge_csv_files(input_dir="/Users/shuo.yuan/Downloads",
                    output_prefix="dau汇总"):
    """
    合并多个CSV文件并按渠道分组保存，保留原始N/A值

    参数:
    input_dir (str): 包含CSV文件的目录，默认为用户下载文件夹
    output_prefix (str): 输出文件前缀，默认为"dau汇总"
    """
    print("=" * 50)
    print("CSV文件合并工具 - 开始处理")
    print("=" * 50)

    # 验证步骤1: 检查输入目录是否存在
    try:
        if not os.path.exists(input_dir):
            print(f"错误: 指定的目录不存在: {input_dir}")
            return None
        print(f"✓ 步骤1: 成功验证输入目录: {input_dir}")
    except Exception as e:
        print(f"错误: 验证输入目录时出错: {str(e)}")
        return None

    # 获取当前日期作为文件名的一部分
    today = datetime.datetime.now().strftime("%m.%d")
    output_base = f"{today} {output_prefix}"

    # 获取目录中所有CSV文件
    try:
        csv_files = glob.glob(os.path.join(input_dir, '*.csv'))

        if not csv_files:
            print(f"警告: 指定目录中未找到CSV文件: {input_dir}")
            return None

        print(f"✓ 步骤2: 找到{len(csv_files)}个CSV文件")
    except Exception as e:
        print(f"错误: 查找CSV文件时出错: {str(e)}")
        return None

    # 创建一个字典来存储每个渠道的DataFrame列表
    channel_dfs = {'mvp': [], 'and': [], 'ios': []}

    # 为每个渠道存储标准列名
    standard_columns = {
        'mvp': None,
        'and': None,
        'ios': None
    }

    processed_files = 0

    # 验证步骤3: 读取和处理每个CSV文件
    print("\n正在处理文件...")
    for file in csv_files:
        try:
            # 检查文件名是否包含"dau"
            if "dau" not in os.path.basename(file).lower():
                continue

            filename = os.path.basename(file)
            print(f"\n处理文件: {filename}")

            # 从文件名中提取渠道信息
            if len(filename) > 7 and filename.startswith("dau_"):
                channel = filename[4:7]  # 获取渠道名 (mvp, and, ios)
                if channel not in channel_dfs:
                    print(f"  - 警告: 无法识别的渠道 '{channel}'，已跳过")
                    continue
            else:
                print(f"  - 警告: 文件名 {filename} 格式不符合预期，已跳过")
                continue

            # 尝试检测编码并保留N/A值
            try:
                # 使用na_values和keep_default_na参数来保留原始的"N/A"字符串
                df = pd.read_csv(file, encoding='utf-8', na_values=[''], keep_default_na=False)
                print(f"  - 使用UTF-8编码成功读取")
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(file, encoding='latin1', na_values=[''], keep_default_na=False)
                    print(f"  - 使用Latin-1编码成功读取")
                except Exception:
                    print(f"  - 错误: 无法使用UTF-8或Latin-1编码读取文件")
                    continue

            # 验证数据不为空
            if df.empty:
                print(f"  - 警告: 文件 {filename} 不包含数据，已跳过")
                continue

            print(f"  - 原始数据形状: {df.shape}")

            # 打印列名，用于调试
            print(f"  - 列名: {', '.join(df.columns.tolist())}")

            # 删除指定的三列（如果存在）
            columns_to_drop = ['Total Conversions', 'Re-attribution', 'Re-engagement']
            original_cols = df.columns.tolist()
            df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')
            removed_cols = [col for col in columns_to_drop if col in original_cols]
            if removed_cols:
                print(f"  - 已删除列: {', '.join(removed_cols)}")

            # 从文件名提取日期部分并格式化为 2025/3/17 格式
            try:
                date_part = filename.split('_')[-1].replace('.csv', '')
                # 提取月份和日期
                match = re.search(r'(\d+)\.(\d+)', date_part)
                if match:
                    month, day = match.groups()
                    formatted_date = f"2025/{month}/{day}"  # 使用2025年作为固定年份
                else:
                    formatted_date = date_part
                print(f"  - 提取的日期: {formatted_date}")
            except:
                formatted_date = "2025/1/1"  # 默认日期
                print(f"  - 警告: 无法从文件名提取日期，使用默认值 '{formatted_date}'")

            # 添加日期列到DataFrame的最前面
            df.insert(0, 'date', formatted_date)  # 使用小写'date'作为列名

            # 如果是iOS渠道且发现有问题的列
            if channel == 'ios' and 'Average eCPIUS$2.50' in df.columns:
                print(f"  - 发现有问题的列 'Average eCPIUS$2.50'，将被移除")
                df = df.drop(columns=['Average eCPIUS$2.50'])

            # 列标准化：确保每个渠道的数据使用一致的列名
            if standard_columns[channel] is None:
                # 第一次遇到该渠道的数据，设置为标准列
                standard_columns[channel] = df.columns.tolist()
                print(f"  - 设置 {channel} 渠道的标准列为: {', '.join(standard_columns[channel])}")
            else:
                # 检查列名是否与之前的一致
                current_cols = df.columns.tolist()
                if current_cols != standard_columns[channel]:
                    print(f"  - 警告: 列名与标准不一致")
                    print(f"    标准列: {', '.join(standard_columns[channel])}")
                    print(f"    当前列: {', '.join(current_cols)}")

                    # 调整列名以匹配标准列（仅保留标准列中存在的列）
                    missing_cols = [col for col in standard_columns[channel] if col not in current_cols]
                    extra_cols = [col for col in current_cols if col not in standard_columns[channel]]

                    if missing_cols:
                        print(f"    缺少的列: {', '.join(missing_cols)}")
                        # 为缺少的列添加NaN值
                        for col in missing_cols:
                            df[col] = 'N/A'

                    if extra_cols:
                        print(f"    多余的列: {', '.join(extra_cols)}")
                        # 移除多余的列
                        df = df.drop(columns=extra_cols)

                    # 确保列顺序一致
                    df = df[standard_columns[channel]]

            # 将真正的空值转换为"N/A"
            df = df.fillna('N/A')

            # 根据渠道分组
            channel_dfs[channel].append(df)
            print(f"  - 成功处理: 形状 {df.shape}, 渠道: {channel}")
            processed_files += 1

        except Exception as e:
            print(f"  - 错误: 处理文件 {file} 时失败: {str(e)}")
            # 打印详细的错误跟踪信息
            import traceback
            print(traceback.format_exc())

    if processed_files == 0:
        print("\n错误: 没有成功处理任何文件")
        return None

    print(f"\n✓ 步骤3: 成功处理了 {processed_files} 个文件")

    # 验证步骤4: 合并数据并按日期排序
    print("\n开始合并数据并按日期排序...")

    # 创建一个字典来存储每个渠道的合并DataFrame
    merged_by_channel = {}
    total_rows = 0

    # 日期转换函数 - 用于排序
    def convert_date_to_sortable(date_str):
        try:
            # 预期格式为 "2025/3/17"
            parts = date_str.split('/')
            if len(parts) == 3:
                year, month, day = parts
                # 确保月份和日期都是两位数
                month = month.zfill(2)
                day = day.zfill(2)
                # 返回排序键
                return f"{year}{month}{day}"
        except:
            pass
        # 如果无法解析，返回原始字符串
        return date_str

    # 合并每个渠道的数据
    for channel, df_list in channel_dfs.items():
        try:
            if df_list:
                print(f"\n处理渠道: {channel}")
                print(f"  - 找到 {len(df_list)} 个文件属于此渠道")

                # 检查所有DataFrame的列是否一致
                column_sets = [set(df.columns) for df in df_list]
                all_same = all(cols == column_sets[0] for cols in column_sets)

                if not all_same:
                    print(f"  - 警告: 该渠道中的文件列名不一致")
                    # 使用第一个文件的列作为标准
                    standard_cols = list(df_list[0].columns)
                    print(f"  - 使用标准列: {', '.join(standard_cols)}")

                    # 确保所有DataFrame都有相同的列
                    for i, df in enumerate(df_list):
                        if set(df.columns) != set(standard_cols):
                            missing = [col for col in standard_cols if col not in df.columns]
                            extra = [col for col in df.columns if col not in standard_cols]

                            # 添加缺失的列
                            for col in missing:
                                df[col] = 'N/A'

                            # 删除多余的列
                            if extra:
                                df = df.drop(columns=extra)

                            # 重新排序列
                            df = df[standard_cols]
                            df_list[i] = df

                # 合并该渠道的所有DataFrame
                merged_df = pd.concat(df_list, ignore_index=True)
                row_count = len(merged_df)
                print(f"  - 合并后形状: {merged_df.shape}")
                print(f"  - 合并后列名: {', '.join(merged_df.columns.tolist())}")

                # 按日期排序
                try:
                    # 创建一个临时列用于排序
                    merged_df['sort_key'] = merged_df['date'].apply(convert_date_to_sortable)

                    # 按排序键排序
                    merged_df = merged_df.sort_values(by='sort_key')

                    # 删除临时排序列
                    merged_df = merged_df.drop(columns=['sort_key'])

                    print(f"  - 已按日期排序数据")
                except Exception as e:
                    print(f"  - 警告: 排序时出错: {str(e)}")

                # 确保任何新生成的空值转换为N/A
                merged_df = merged_df.fillna('N/A')

                # 特殊处理iOS渠道，确保没有多余的列
                if channel == 'ios':
                    expected_columns = ['date', 'Country', 'Impressions', 'Clicks', 'Installs', 'Conversion Rate',
                                        'Activity Sessions', 'Cost', 'Activity Revenue', 'Average eCPIUS$2.31',
                                        'Average DAU', 'Average MAU', 'Average DAU/MAU Rate', 'ARPDAU']

                    # 检查是否有预期之外的列
                    extra_columns = [col for col in merged_df.columns if col not in expected_columns]
                    if extra_columns:
                        print(f"  - 移除iOS中的多余列: {', '.join(extra_columns)}")
                        merged_df = merged_df.drop(columns=extra_columns)

                    # 检查是否缺少预期的列
                    missing_columns = [col for col in expected_columns if col not in merged_df.columns]
                    if missing_columns:
                        print(f"  - iOS数据缺少列: {', '.join(missing_columns)}")
                        for col in missing_columns:
                            merged_df[col] = 'N/A'

                    # 确保列顺序一致
                    merged_df = merged_df[expected_columns]

                merged_by_channel[channel] = merged_df

                # 保存到子文件
                channel_output = os.path.join(input_dir, f"{output_base}_{channel}.csv")
                merged_df.to_csv(channel_output, index=False, encoding='utf-8')
                print(f"  - 已保存到: {channel_output}")
                print(f"  - 行数: {len(merged_df)}")

                total_rows += len(merged_df)
        except Exception as e:
            print(f"  - 错误: 处理渠道 {channel} 时失败: {str(e)}")
            # 打印详细的错误跟踪信息
            import traceback
            print(traceback.format_exc())

    if not merged_by_channel:
        print("\n错误: 没有成功合并任何数据")
        return None

    print(f"\n✓ 步骤4: 成功合并了 {len(merged_by_channel)} 个渠道的数据")
    print("\n" + "=" * 50)
    print("处理完成!")
    print("=" * 50)

    return merged_by_channel


# 直接运行脚本
if __name__ == "__main__":
    try:
        # 使用指定的下载路径
        input_directory = "/Users/shuo.yuan/Downloads"

        # 合并CSV文件
        channel_data = merge_csv_files(input_directory)

        # 显示处理结果摘要
        if channel_data is not None:
            print("\n处理结果摘要:")
            for channel, df in channel_data.items():
                print(f"- 渠道 {channel}: {len(df)} 行数据")

                # 显示排序后的日期顺序（仅显示前5个和后5个日期，如果数据足够）
                all_dates = df['date'].unique()
                if len(all_dates) > 0:
                    sample_dates = list(all_dates)
                    if len(sample_dates) > 10:
                        date_preview = sample_dates[:5] + ['...'] + sample_dates[-5:]
                    else:
                        date_preview = sample_dates
                    print(f"  日期顺序: {' -> '.join(date_preview)}")

            print("\n文件已保存到下载文件夹。")

    except Exception as e:
        print(f"\n程序运行时发生严重错误: {str(e)}")
        # 输出完整的错误跟踪信息
        import traceback

        print("\n详细错误信息:")
        traceback.print_exc()