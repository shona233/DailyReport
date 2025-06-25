import pandas as pd
import os
import sys
import re
from pathlib import Path


def process_retention_files(directory_path):
    """
    处理四个渠道的留存率数据文件

    每个渠道的特殊规则：
    - ios: 添加4个空列，计算day1至day7、day14、day30的留存率
    - ios_formal: 添加4个空列，计算day1至day7、day14、day30的留存率
    - mvp: 添加1个空列，计算day1至day7、day14的留存率
    - and: 不添加空列，计算day1至day7、day14、day30的留存率

    参数:
    directory_path: 包含CSV文件的目录路径
    """
    # 定义四个渠道及其对应的文件模式
    channels = {
        'ios': {
            'pattern': r'^retention_ios(?!_formal).*\.csv$',  # 匹配iOS文件名但排除ios_formal
            'empty_columns': 4,
            'days': list(range(1, 8)) + [14, 30]
        },
        'ios_formal': {
            'pattern': r'^retention_ios_formal.*\.csv$',  # 匹配包含日期的iOS formal文件名
            'empty_columns': 3,
            'days': list(range(1, 8)) + [14, 30]
        },
        'mvp': {
            'pattern': r'^retention_mvp.*\.csv$',  # 匹配包含日期的MVP文件名
            'empty_columns': 1,
            'days': list(range(1, 8)) + [14]
        },
        'and': {
            'pattern': r'^retention_and.*\.csv$',  # 匹配包含日期的Android文件名
            'empty_columns': 0,
            'days': list(range(1, 8)) + [14, 30]
        }
    }

    # 设置工作目录
    try:
        os.chdir(directory_path)
        print(f"已切换到工作目录: {directory_path}")
    except Exception as e:
        print(f"切换工作目录时出错: {str(e)}")
        print(f"当前工作目录: {os.getcwd()}")
        return

    # 列出目录中的所有CSV文件
    print("\n当前目录中的CSV文件:")
    csv_files = [f for f in os.listdir('.') if f.lower().endswith('.csv')]
    for file in csv_files:
        print(f" - {file}")

    # 找到每个渠道对应的文件
    channel_files = {}
    for channel_name, channel_info in channels.items():
        pattern = re.compile(channel_info['pattern'])
        matching_files = [f for f in csv_files if pattern.match(f)]

        if matching_files:
            # 如果有多个匹配的文件，使用最新的那个（按文件名排序，通常日期在后面）
            file_name = sorted(matching_files)[-1]
            channel_files[channel_name] = file_name
            print(f"找到 {channel_name} 渠道的文件: {file_name}")
        else:
            print(f"警告: 未找到 {channel_name} 渠道的文件")

    # 显示未找到文件的渠道
    missing_channels = set(channels.keys()) - set(channel_files.keys())
    if missing_channels:
        print(f"\n注意: 以下 {len(missing_channels)} 个渠道的文件未找到:")
        for channel in missing_channels:
            print(f" - {channel}")
        print("请确认文件名和路径是否正确。")

    # 处理每个渠道的文件
    for channel_name, file_name in channel_files.items():
        channel_info = channels[channel_name]
        empty_col_count = channel_info['empty_columns']
        retention_days = channel_info['days']

        print(f"\n正在处理 {channel_name} 渠道的数据...")
        print(f"规则: {'添加' + str(empty_col_count) + '个空列' if empty_col_count > 0 else '不添加空列'}, "
              f"计算day1至day7、{'day14' if 14 in retention_days else ''}{'、day30' if 30 in retention_days else ''}的留存率")

        try:
            # 读取CSV文件，尝试不同的编码
            print(f"尝试读取文件: {file_name}，完整路径: {os.path.abspath(file_name)}")

            # 尝试常见的编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin1', 'ISO-8859-1', 'windows-1252']
            df = None

            for encoding in encodings:
                try:
                    print(f"尝试使用 {encoding} 编码读取...")
                    df = pd.read_csv(file_name, encoding=encoding)
                    print(f"成功使用 {encoding} 编码读取文件")
                    break
                except UnicodeDecodeError:
                    print(f"{encoding} 编码读取失败，尝试下一种编码")
                except Exception as e:
                    print(f"使用 {encoding} 编码时发生其他错误: {str(e)}")

            if df is None:
                print(f"无法使用任何编码读取文件 {file_name}，跳过处理")
                continue

            # 输出文件的基本信息
            print(f"文件 {file_name} 成功加载，包含 {len(df)} 行和 {len(df.columns)} 列")

            # 使用 "Cohort Day" 作为日期列
            date_column = "Cohort Day"

            # 检查日期列是否存在
            if date_column not in df.columns:
                print(f"警告: 在 {file_name} 中没有找到 '{date_column}' 列")
                # 尝试其他可能的日期列名
                possible_date_columns = ['Date', 'date', '日期', 'DAY', 'Day', 'day']
                for col in possible_date_columns:
                    if col in df.columns:
                        date_column = col
                        print(f"使用替代日期列: '{date_column}'")
                        break

                if date_column not in df.columns:
                    print(f"无法找到日期列，无法排序数据。")
                    date_column = None

            # 排序数据
            if date_column:
                try:
                    df[date_column] = pd.to_datetime(df[date_column])
                    df = df.sort_values(by=date_column)
                    print(f"已按照 '{date_column}' 列排序")
                except Exception as e:
                    print(f"警告: 无法将 {date_column} 列转换为日期类型: {str(e)}")
                    # 尝试按照字符串排序
                    try:
                        df = df.sort_values(by=date_column)
                        print(f"已按照 '{date_column}' 列(字符串类型)排序")
                    except:
                        print(f"无法排序数据")

            # 检查是否存在Users列
            users_column = 'Users'
            if users_column not in df.columns:
                print(f"警告: 在 {file_name} 中没有找到 'Users' 列")
                possible_users_columns = ['users', '用户数', 'DAU', 'User Count', 'user_count']
                for col in possible_users_columns:
                    if col in df.columns:
                        users_column = col
                        print(f"使用替代用户列: '{users_column}'")
                        break

                if users_column not in df.columns:
                    print(f"无法找到用户列，无法计算留存率")
                    continue

            # 添加空列
            for i in range(empty_col_count):
                df[' ' * (i + 1)] = None

            # 计算留存率
            for day in retention_days:
                # 尝试两种可能的列名格式
                retention_columns = [
                    f'sessions - Unique users - day {day}- partial',  # 不带空格
                    f'sessions - Unique users - day {day}',
                    f'sessions - Unique users - day {day} - partial'  # 带空格
                ]

                # 找到第一个存在的列名
                retention_column = next((col for col in retention_columns if col in df.columns), None)

                if retention_column:
                    df[f'day{day}'] = (df[retention_column] / df[users_column]).round(4)
                    print(f"已计算 day{day} 留存率")
                else:
                    print(f"警告: 在 {file_name} 中没有找到 day{day} 相关的列，无法计算 day{day} 留存率")

            # 保存处理后的文件
            output_file = f'【排序】{file_name}'
            df.to_csv(output_file, index=False)
            print(f"已处理并保存到 {output_file}")

        except Exception as e:
            print(f"处理 {file_name} 时出错: {str(e)}")

    print("\n所有文件处理完成！")


if __name__ == "__main__":
    # 获取命令行参数或使用默认路径
    if len(sys.argv) > 1:
        directory_path = sys.argv[1]
    else:
        directory_path = '/Users/shuo.yuan/Downloads'

    print(f"使用目录路径: {directory_path}")
    if not os.path.exists(directory_path):
        print(f"错误: 目录 {directory_path} 不存在!")
        sys.exit(1)

    print(f"目录存在: {directory_path}")
    process_retention_files(directory_path)