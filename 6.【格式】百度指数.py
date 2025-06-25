import re
import os
import pandas as pd
from datetime import datetime, timedelta

def extract_data_from_text(text):
    # 提取日期
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    stat_date = date_match.group(1) if date_match else None
    
    # 如果没有找到日期，使用默认日期
    if not stat_date:
        stat_date = "2025-04-02"
    
    # 计算ID (默认2025-04-02对应的是3390，依次往后递增)
    base_date = datetime.strptime("2025-04-02", "%Y-%m-%d")
    current_date = datetime.strptime(stat_date, "%Y-%m-%d")
    days_diff = (current_date - base_date).days
    id_value = 3390 + days_diff
    
    # 提取各项指数
    # 天气
    weather_match = re.search(r'天气\s*([\d,]+)', text)
    weather_search_index = weather_match.group(1).replace(',', '') if weather_match else "0"
    
    # 天气预报
    forecast_match = re.search(r'天气预报\s*([\d,]+)', text)
    weather_forcast_search_index = forecast_match.group(1).replace(',', '') if forecast_match else "0"
    
    # 计算天气和天气预报的总和
    try:
        weather_and_forcast = int(weather_search_index) + int(weather_forcast_search_index)
    except ValueError:
        weather_and_forcast = 0
    
    # 台风
    typhoon_match = re.search(r'台风\s*([\d,]+)', text)
    typhoon_search_index = typhoon_match.group(1).replace(',', '') if typhoon_match else "0"
    
    # 墨迹天气
    moji_match = re.search(r'墨迹天气\s*(?:@百度指)?\s*([\d,]+)', text)
    moji_weather = moji_match.group(1).replace(',', '') if moji_match else "0"
    
    # 构建结果字典
    result = {
        "id": id_value,
        "stat_date": stat_date,
        "weather_search_index": int(weather_search_index),
        "weather_forcast_search_index": int(weather_forcast_search_index),
        "weather_and_forcast": weather_and_forcast,
        "typhoon_search_index": int(typhoon_search_index),
        "moji_weather": int(moji_weather)
    }
    
    return result

def format_output_two_lines(data):
    # 第一行：表头
    headers = ["id", "stat_date", "weather_search_index", "weather_forcast_search_index", 
               "weather_and_forcast", "typhoon_search_index", "moji_weather"]
    header_line = "\t".join(headers)
    
    # 第二行：值
    values = [
        str(data['id']),
        data['stat_date'],
        str(data['weather_search_index']),
        str(data['weather_forcast_search_index']),
        str(data['weather_and_forcast']),
        str(data['typhoon_search_index']),
        str(data['moji_weather'])
    ]
    value_line = "\t".join(values)
    
    return header_line + "\n" + value_line

def append_to_excel(data, excel_path):
    """
    将新数据追加到Excel文件的最后一行
    
    参数:
    data (dict): 要追加的数据字典
    excel_path (str): Excel文件路径
    
    返回:
    bool: 操作是否成功
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(excel_path):
            print(f"警告: 文件不存在: {excel_path}")
            print("将创建新文件")
            
            # 创建一个新的DataFrame
            df = pd.DataFrame([data])
            
            # 保存为Excel
            df.to_excel(excel_path, index=False)
            return True
        
        # 读取现有Excel文件
        df = pd.read_excel(excel_path)
        
        # 打印现有数据的基本信息
        print(f"现有数据: {len(df)}行, {len(df.columns)}列")
        print(f"列名: {', '.join(df.columns.tolist())}")
        
        # 检查列名是否匹配
        expected_columns = ["id", "stat_date", "weather_search_index", "weather_forcast_search_index", 
                           "weather_and_forcast", "typhoon_search_index", "moji_weather"]
        
        # 检查列名是否存在（不区分大小写）
        lower_columns = [col.lower() for col in df.columns]
        matching_columns = all(col.lower() in lower_columns for col in expected_columns)
        
        if not matching_columns:
            print("警告: Excel文件的列名与预期不匹配")
            print(f"预期列名: {', '.join(expected_columns)}")
            print(f"实际列名: {', '.join(df.columns.tolist())}")
            
            user_input = input("是否仍要继续? (y/n): ").lower()
            if user_input != 'y':
                print("操作已取消")
                return False
        
        # 检查是否已存在相同日期的数据
        if "stat_date" in df.columns:
            existing_dates = df["stat_date"].astype(str).tolist()
            if data["stat_date"] in existing_dates:
                print(f"警告: 数据中已存在日期 {data['stat_date']} 的记录")
                
                user_input = input("是否仍要添加? (y/n): ").lower()
                if user_input != 'y':
                    print("操作已取消")
                    return False
        
        # 将新数据添加到DataFrame
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        
        # 保存更新后的DataFrame回Excel文件
        df.to_excel(excel_path, index=False)
        
        print(f"成功将新数据添加到 {excel_path}")
        print(f"现在共有 {len(df)} 行数据")
        return True
    
    except Exception as e:
        print(f"将数据添加到Excel时出错: {str(e)}")
        return False

def main():
    # 设置Excel文件路径
    excel_path = os.path.expanduser("~/Downloads/(0) 百度指数实时更新.xlsx")
    
    print("请输入百度指数文本数据 (直接粘贴所有文本，完成后按回车两次):")
    
    # 收集多行输入
    lines = []
    while True:
        line = input()
        if not line:  # 空行表示输入结束
            break
        lines.append(line)
    
    # 将所有行合并成一个字符串
    input_text = " ".join(lines)
    
    # 提取数据并格式化输出
    try:
        # 解析输入数据
        data = extract_data_from_text(input_text)
        
        # 格式化并显示输出
        formatted_output = format_output_two_lines(data)
        print("\n处理结果:")
        print(formatted_output)
        
        # 追加到Excel文件
        print(f"\n准备将数据追加到: {excel_path}")
        if append_to_excel(data, excel_path):
            print("数据已成功添加到Excel文件")
        else:
            print("添加数据失败")
        
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
import re
import os
import pandas as pd
from datetime import datetime, timedelta

def extract_data_from_text(text):
    # 提取日期
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    stat_date = date_match.group(1) if date_match else None
    
    # 如果没有找到日期，使用默认日期
    if not stat_date:
        stat_date = "2025-04-02"
    
    # 计算ID (默认2025-04-02对应的是3390，依次往后递增)
    base_date = datetime.strptime("2025-04-02", "%Y-%m-%d")
    current_date = datetime.strptime(stat_date, "%Y-%m-%d")
    days_diff = (current_date - base_date).days
    id_value = 3390 + days_diff
    
    # 提取各项指数
    # 天气
    weather_match = re.search(r'天气\s*([\d,]+)', text)
    weather_search_index = weather_match.group(1).replace(',', '') if weather_match else "0"
    
    # 天气预报
    forecast_match = re.search(r'天气预报\s*([\d,]+)', text)
    weather_forcast_search_index = forecast_match.group(1).replace(',', '') if forecast_match else "0"
    
    # 计算天气和天气预报的总和
    try:
        weather_and_forcast = int(weather_search_index) + int(weather_forcast_search_index)
    except ValueError:
        weather_and_forcast = 0
    
    # 台风
    typhoon_match = re.search(r'台风\s*([\d,]+)', text)
    typhoon_search_index = typhoon_match.group(1).replace(',', '') if typhoon_match else "0"
    
    # 墨迹天气
    moji_match = re.search(r'墨迹天气\s*(?:@百度指)?\s*([\d,]+)', text)
    moji_weather = moji_match.group(1).replace(',', '') if moji_match else "0"
    
    # 构建结果字典
    result = {
        "id": id_value,
        "stat_date": stat_date,
        "weather_search_index": int(weather_search_index),
        "weather_forcast_search_index": int(weather_forcast_search_index),
        "weather_and_forcast": weather_and_forcast,
        "typhoon_search_index": int(typhoon_search_index),
        "moji_weather": int(moji_weather)
    }
    
    return result

def format_output_two_lines(data):
    # 第一行：表头
    headers = ["id", "stat_date", "weather_search_index", "weather_forcast_search_index", 
               "weather_and_forcast", "typhoon_search_index", "moji_weather"]
    header_line = "\t".join(headers)
    
    # 第二行：值
    values = [
        str(data['id']),
        data['stat_date'],
        str(data['weather_search_index']),
        str(data['weather_forcast_search_index']),
        str(data['weather_and_forcast']),
        str(data['typhoon_search_index']),
        str(data['moji_weather'])
    ]
    value_line = "\t".join(values)
    
    return header_line + "\n" + value_line

def append_to_excel(data, excel_path):
    """
    将新数据追加到Excel文件的最后一行
    
    参数:
    data (dict): 要追加的数据字典
    excel_path (str): Excel文件路径
    
    返回:
    bool: 操作是否成功
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(excel_path):
            print(f"警告: 文件不存在: {excel_path}")
            print("将创建新文件")
            
            # 创建一个新的DataFrame
            df = pd.DataFrame([data])
            
            # 保存为Excel
            df.to_excel(excel_path, index=False)
            return True
        
        # 读取现有Excel文件
        df = pd.read_excel(excel_path)
        
        # 打印现有数据的基本信息
        print(f"现有数据: {len(df)}行, {len(df.columns)}列")
        print(f"列名: {', '.join(df.columns.tolist())}")
        
        # 检查列名是否匹配
        expected_columns = ["id", "stat_date", "weather_search_index", "weather_forcast_search_index", 
                           "weather_and_forcast", "typhoon_search_index", "moji_weather"]
        
        # 检查列名是否存在（不区分大小写）
        lower_columns = [col.lower() for col in df.columns]
        matching_columns = all(col.lower() in lower_columns for col in expected_columns)
        
        if not matching_columns:
            print("警告: Excel文件的列名与预期不匹配")
            print(f"预期列名: {', '.join(expected_columns)}")
            print(f"实际列名: {', '.join(df.columns.tolist())}")
            
            user_input = input("是否仍要继续? (y/n): ").lower()
            if user_input != 'y':
                print("操作已取消")
                return False
        
        # 检查是否已存在相同日期的数据
        if "stat_date" in df.columns:
            existing_dates = df["stat_date"].astype(str).tolist()
            if data["stat_date"] in existing_dates:
                print(f"警告: 数据中已存在日期 {data['stat_date']} 的记录")
                
                user_input = input("是否仍要添加? (y/n): ").lower()
                if user_input != 'y':
                    print("操作已取消")
                    return False
        
        # 将新数据添加到DataFrame
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        
        # 保存更新后的DataFrame回Excel文件
        df.to_excel(excel_path, index=False)
        
        print(f"成功将新数据添加到 {excel_path}")
        print(f"现在共有 {len(df)} 行数据")
        return True
    
    except Exception as e:
        print(f"将数据添加到Excel时出错: {str(e)}")
        return False

def main():
    # 设置Excel文件路径
    excel_path = os.path.expanduser("~/Downloads/(0) 百度指数实时更新.xlsx")
    
    print("请输入百度指数文本数据 (直接粘贴所有文本，完成后按回车两次):")
    
    # 收集多行输入
    lines = []
    while True:
        line = input()
        if not line:  # 空行表示输入结束
            break
        lines.append(line)
    
    # 将所有行合并成一个字符串
    input_text = " ".join(lines)
    
    # 提取数据并格式化输出
    try:
        # 解析输入数据
        data = extract_data_from_text(input_text)
        
        # 格式化并显示输出
        formatted_output = format_output_two_lines(data)
        print("\n处理结果:")
        print(formatted_output)
        
        # 追加到Excel文件
        print(f"\n准备将数据追加到: {excel_path}")
        if append_to_excel(data, excel_path):
            print("数据已成功添加到Excel文件")
        else:
            print("添加数据失败")
        
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
