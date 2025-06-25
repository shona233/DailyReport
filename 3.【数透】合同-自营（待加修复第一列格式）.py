import pandas as pd
import os
from datetime import datetime, timedelta
import re

def find_contract_file(directory):
    """查找目录中符合'合同数据按天导出表+一串数字'模式的CSV文件"""
    pattern = re.compile(r'合同数据按天导出表.*\.csv')
    
    print(f"正在搜索目录: {directory}")
    try:
        files = os.listdir(directory)
        print(f"目录中共有 {len(files)} 个文件")
        
        for file in files:
            print(f"检查文件: {file}")
            if pattern.match(file):
                full_path = os.path.join(directory, file)
                print(f"找到匹配的文件: {full_path}")
                return full_path
        
        print("没有找到匹配的文件")
        
        # 如果没有找到匹配的文件，让用户手动输入
        user_input = input("未找到匹配的合同文件，是否要手动输入文件路径? (y/n): ")
        if user_input.lower() == 'y':
            file_path = input("请输入完整的CSV文件路径: ")
            if os.path.exists(file_path) and file_path.endswith('.csv'):
                return file_path
    
    except Exception as e:
        print(f"查找文件时出错: {e}")
    
    return None

def process_contract_data(file_path):
    # 读取CSV文件
    print(f"正在读取文件: {file_path}")
    # 尝试不同编码读取文件
    encodings = ['utf-8-sig', 'gbk', 'gb18030', 'gb2312', 'latin1']
    
    for encoding in encodings:
        try:
            print(f"尝试使用 {encoding} 编码读取文件...")
            df = pd.read_csv(file_path, encoding=encoding)
            print(f"成功使用 {encoding} 编码读取文件")
            break
        except UnicodeDecodeError:
            print(f"{encoding} 编码读取失败，尝试下一种编码...")
        except Exception as e:
            print(f"读取文件时出现其他错误: {e}")
    else:
        print("所有编码尝试均失败，无法读取文件")
        return None
    
    # 确认文件已正确读取
    print(f"成功读取数据，共 {len(df)} 行")
    
    # 设置默认日期为前一天
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')  # 格式为YYYYMMDD
    default_date = yesterday  # 完整的日期，如20250331
    
    # 询问用户是否修改日期筛选
    print(f"默认筛选日期为 {default_date} ({default_date[:4]}年{default_date[4:6]}月{default_date[6:8]}日)")
    user_input = input(f"是否需要修改? (y/n): ")
    
    if user_input.lower() == 'y':
        date_input = input("请输入筛选日期 (格式 YYYYMMDD，如20250331): ")
        if date_input.isdigit() and len(date_input) == 8:
            filter_date = date_input
        else:
            print(f"输入格式不正确，使用默认值 {default_date}")
            filter_date = default_date
    else:
        filter_date = default_date
    
    # 从日期中提取年月部分用于筛选
    year_month = filter_date[:6]
    
    print(f"筛选日期: {filter_date} ({filter_date[:4]}年{filter_date[4:6]}月{filter_date[6:8]}日)")
    print(f"对应的年月: {year_month}")
    
    # 设置默认按精确日期筛选，不再询问用户
    filter_exact_day = True
    print(f"将按精确日期 {filter_date} 进行筛选")
    
    # 处理日期筛选
    try:
        # 检查'年份月份'列是否存在
        if '年份月份' in df.columns:
            print("找到'年份月份'列")
            # 检查一些样本值
            sample_values = df['年份月份'].dropna().head(5).tolist()
            print(f"'年份月份'列的样本值: {sample_values}")
            
            # 将'年份月份'转换为字符串并清理
            df['年份月份'] = df['年份月份'].astype(str).str.strip()
            
            # 检查数值列的数据格式
            for col in ['后台实际营收(无余量)', '曝光(无余量)']:
                if col in df.columns:
                    print(f"检查 '{col}' 列的数据类型和样本值")
                    print(f"数据类型: {df[col].dtype}")
                    sample_values = df[col].dropna().head(5).tolist()
                    print(f"样本值: {sample_values}")
                    
                    # 尝试将列转换为数值型
                    try:
                        # 如果是字符串类型，需要预处理
                        if df[col].dtype == 'object':
                            # 移除非数字字符（除了小数点和负号）
                            df[col] = df[col].astype(str).str.replace(',', '')  # 移除千位分隔符
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            print(f"已将 '{col}' 转换为数值类型")
                    except Exception as e:
                        print(f"转换 '{col}' 列为数值类型时出错: {e}")
                else:
                    print(f"警告: 未找到 '{col}' 列")
            
            # 完整日期筛选 - 如果需要精确到日
            if filter_exact_day:
                print(f"进行精确日期筛选: {filter_date}")
                df_filtered = df[df['年份月份'] == filter_date]
                if len(df_filtered) == 0:
                    print("警告: 精确日期筛选没有匹配的数据")
                    print("尝试使用年月筛选...")
                    df_filtered = df[df['年份月份'].str.startswith(year_month)]
            # 年月筛选
            else:
                print(f"进行年月筛选: {year_month}")
                df_filtered = df[df['年份月份'].str.startswith(year_month)]
            
            print(f"筛选后数据行数: {len(df_filtered)}")
            if len(df_filtered) == 0:
                print("警告: 筛选后没有数据，请检查日期格式是否匹配")
                
                # 显示一些样本日期值
                sample_dates = sorted(df['年份月份'].dropna().unique().tolist())[:20]
                print(f"数据中的一些日期样本: {sample_dates}")
                
                # 询问是否继续处理
                user_input = input("筛选后没有数据，是否要处理所有数据? (y/n): ")
                if user_input.lower() == 'y':
                    df_filtered = df
                else:
                    return None
        else:
            print("未找到'年份月份'列")
            print(f"可用的列: {df.columns.tolist()}")
            
            # 查找可能的日期列
            date_columns = [col for col in df.columns if '年' in col or '月' in col or '日' in col or 'date' in col.lower()]
            if date_columns:
                print(f"找到可能的日期列: {date_columns}")
                user_choice = input(f"请选择要用于日期筛选的列 (输入序号1-{len(date_columns)}), 或输入0处理所有数据: ")
                
                if user_choice.isdigit() and int(user_choice) > 0 and int(user_choice) <= len(date_columns):
                    date_column = date_columns[int(user_choice) - 1]
                    # 特定处理逻辑
                    # ...
                else:
                    print("处理所有数据")
                    df_filtered = df
            else:
                print("未找到可能的日期列，处理所有数据")
                df_filtered = df
    except Exception as e:
        print(f"日期筛选过程出错: {e}")
        import traceback
        traceback.print_exc()
        user_input = input("日期筛选出错，是否要处理所有数据? (y/n): ")
        if user_input.lower() == 'y':
            df_filtered = df
        else:
            return None
    
    # 创建第一个数据透视表 - 按最终客户求和
    try:
        # 检查所需列是否存在
        required_columns = ['最终客户', '后台实际营收(无余量)', '曝光(无余量)']
        missing_columns = [col for col in required_columns if col not in df_filtered.columns]
        
        if missing_columns:
            print(f"警告: 以下列不存在: {missing_columns}")
            print(f"可用的列: {df_filtered.columns.tolist()}")
            
            # 如果缺少必要列，尝试查找相似的列名
            column_mapping = {}
            for missing_col in missing_columns:
                similar_columns = [col for col in df_filtered.columns if missing_col in col]
                if similar_columns:
                    print(f"找到与 '{missing_col}' 相似的列: {similar_columns}")
                    user_choice = input(f"请选择要用于 '{missing_col}' 的列 (输入序号1-{len(similar_columns)}), 或输入0跳过: ")
                    if user_choice.isdigit() and 1 <= int(user_choice) <= len(similar_columns):
                        column_mapping[missing_col] = similar_columns[int(user_choice) - 1]
            
            # 如果用户提供了映射，创建一个临时DataFrame用于透视表
            if column_mapping:
                temp_df = df_filtered.copy()
                for target_col, source_col in column_mapping.items():
                    temp_df[target_col] = df_filtered[source_col]
                df_for_pivot = temp_df
            else:
                print("缺少必要的列，无法创建数据透视表")
                return None
        else:
            df_for_pivot = df_filtered
        
        # 创建透视表
        pivot1 = pd.pivot_table(
            df_for_pivot,
            values=['后台实际营收(无余量)', '曝光(无余量)'],
            index=['最终客户'],
            aggfunc='sum'
        )
        
        # 确保数据类型正确
        for col in pivot1.columns:
            if pivot1[col].dtype == 'object':
                try:
                    pivot1[col] = pd.to_numeric(pivot1[col], errors='coerce')
                except:
                    pass  # 如果无法转换为数值，保持原样
        
        # 重置索引，将"最终客户"变为普通列
        pivot1 = pivot1.reset_index()
        
        # 添加"日期"列并放在最前面
        # 将YYYYMMDD格式转换为YYYY/M/D格式
        date_parts = [filter_date[:4], str(int(filter_date[4:6])), str(int(filter_date[6:8]))]
        formatted_date = '/'.join(date_parts)
        pivot1.insert(0, ''
                         ''
                         ''
                         '日期', formatted_date)
        
        # 添加"分类"列并放在最后面
        pivot1['分类'] = '自营'
        
        print("第一个数据透视表创建成功")
    except Exception as e:
        print(f"创建第一个数据透视表出错: {e}")
        pivot1 = pd.DataFrame()
        return None
    
    # 创建第二个数据透视表 - 筛选投放位置包含"Splash"或"splash"的数据
    try:
        # 检查'投放位置'列是否存在
        if '投放位置' not in df_filtered.columns:
            print("警告: '投放位置'列不存在")
            similar_columns = [col for col in df_filtered.columns if '位置' in col or '投放' in col]
            
            if similar_columns:
                print(f"找到可能相关的列: {similar_columns}")
                user_choice = input(f"请选择要用于'投放位置'的列 (输入序号1-{len(similar_columns)}), 或输入0跳过: ")
                
                if user_choice.isdigit() and 1 <= int(user_choice) <= len(similar_columns):
                    position_column = similar_columns[int(user_choice) - 1]
                    print(f"使用 '{position_column}' 作为投放位置列")
                else:
                    print("未选择列，无法创建第二个数据透视表")
                    pivot2 = pd.DataFrame()
                    return pivot1, None  # 只返回第一个透视表
            else:
                print("找不到相关列，无法创建第二个数据透视表")
                pivot2 = pd.DataFrame()
                return pivot1, None  # 只返回第一个透视表
        else:
            position_column = '投放位置'
        
        # 首先筛选包含"Splash"或"splash"的行
        splash_filter = df_filtered[position_column].astype(str).str.contains('splash|Splash', case=False, na=False)
        df_splash = df_filtered[splash_filter]
        
        print(f"筛选到 {len(df_splash)} 行包含 'Splash' 的数据")
        
        # 如果没有匹配的数据，提示用户
        if len(df_splash) == 0:
            print(f"警告: 在'{position_column}'列中没有找到包含'Splash'或'splash'的数据")
            # 显示一些示例值以帮助诊断
            sample_values = df_filtered[position_column].dropna().sample(min(5, len(df_filtered))).tolist()
            print(f"'{position_column}'列的一些示例值: {sample_values}")
            
            pivot2 = pd.DataFrame()
        else:
            # 然后创建数据透视表
            pivot2 = pd.pivot_table(
                df_splash,
                values=['后台实际营收(无余量)', '曝光(无余量)'],
                index=['最终客户'],
                aggfunc='sum'
            )
            
            # 确保数据类型正确
            for col in pivot2.columns:
                if pivot2[col].dtype == 'object':
                    try:
                        pivot2[col] = pd.to_numeric(pivot2[col], errors='coerce')
                    except:
                        pass  # 如果无法转换为数值，保持原样
            
            # 重置索引，将"最终客户"变为普通列
            pivot2 = pivot2.reset_index()
            
            # 添加"日期"列并放在最前面
            # 将YYYYMMDD格式转换为YYYY/M/D格式
            date_parts = [filter_date[:4], str(int(filter_date[4:6])), str(int(filter_date[6:8]))]
            formatted_date = '/'.join(date_parts)
            pivot2.insert(0, '日期', formatted_date)
            
            # 添加"分类"列并放在最后面
            pivot2['分类'] = '自营'
            
            print("第二个数据透视表创建成功")
    except Exception as e:
        print(f"创建第二个数据透视表出错: {e}")
        pivot2 = pd.DataFrame()

    # 加载简称映射表
    abbreviation_path = '/Users/shuo.yuan/Downloads/简称.xlsx'
    try:
        print(f"正在加载简称映射表: {abbreviation_path}")
        abbr_df = pd.read_excel(abbreviation_path)
        print(f"简称映射表加载成功，共 {len(abbr_df)} 行")
        
        # 假设第一列是客户名称，第二列是缩写
        # 确保列名正确
        abbr_columns = abbr_df.columns.tolist()
        print(f"简称映射表列名: {abbr_columns}")
        
        # 查找合适的列
        client_col = 0  # 默认第一列为客户名称
        abbr_col = 1    # 默认第二列为缩写
        
        # 创建映射字典
        abbr_dict = dict(zip(abbr_df.iloc[:, client_col], abbr_df.iloc[:, abbr_col]))
        print(f"创建了 {len(abbr_dict)} 个客户名称到缩写的映射")
        
        # 将简称映射应用到透视表
        print("将简称映射应用到第一个透视表")
        
        # 使用匿名函数映射，如果没有匹配项则保持原样
        pivot1['缩写'] = pivot1['最终客户'].map(lambda x: abbr_dict.get(x, x))
        
        if not pivot2.empty:
            print("将简称映射应用到第二个透视表")
            pivot2['缩写'] = pivot2['最终客户'].map(lambda x: abbr_dict.get(x, x))
        
    except Exception as e:
        print(f"加载或应用简称映射时出错: {e}")
        print("将使用原始客户名称作为缩写")
        
        # 如果无法加载简称映射，使用原始客户名称
        pivot1['缩写'] = pivot1['最终客户']
        if not pivot2.empty:
            pivot2['缩写'] = pivot2['最终客户']

    # 保存到本地Excel文件(先保留原来的逻辑)
    try:
        output_file = os.path.join(os.path.dirname(file_path), f'【数透】合同数据分析_{filter_date}.xlsx')
        
        # 使用ExcelWriter设置格式
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            if not pivot1.empty:
                # 将透视表写入Excel
                pivot1.to_excel(writer, sheet_name='全部数据透视表', index=False)
                
                # 获取工作表以应用格式
                worksheet = writer.sheets['全部数据透视表']
                
                # 设置列宽
                for idx, col in enumerate(pivot1.columns):
                    # 获取列的最大长度
                    max_len = max(
                        pivot1[col].astype(str).map(len).max(),  # 数据的最大长度
                        len(str(col))  # 列名的长度
                    )
                    # 设置列宽（稍微增加一点空间）
                    worksheet.column_dimensions[chr(65 + idx)].width = max_len + 4
                
                print(f"已将第一个数据透视表保存到 '{output_file}'")
            
            if not pivot2.empty:
                # 将透视表写入Excel
                pivot2.to_excel(writer, sheet_name='Splash数据透视表', index=False)
                
                # 获取工作表以应用格式
                worksheet = writer.sheets['Splash数据透视表']
                
                # 设置列宽
                for idx, col in enumerate(pivot2.columns):
                    # 获取列的最大长度
                    max_len = max(
                        pivot2[col].astype(str).map(len).max(),  # 数据的最大长度
                        len(str(col))  # 列名的长度
                    )
                    # 设置列宽（稍微增加一点空间）
                    worksheet.column_dimensions[chr(65 + idx)].width = max_len + 4
                
                print(f"已将第二个数据透视表保存到 '{output_file}'")
        
        print(f"数据已保存至: {output_file}")
    except Exception as e:
        print(f"保存Excel文件时出错: {e}")
        import traceback
        traceback.print_exc()

    # 添加到外包自营.xlsx文件
    try:
        # 调整列名以匹配"总"表的要求
        target_file = '/Users/shuo.yuan/Downloads/外包自营.xlsx'
        print(f"正在将数据添加到目标文件: {target_file}")
        
        # 读取目标Excel文件的所有Sheet
        try:
            # 读取Excel文件中的所有表
            xls = pd.ExcelFile(target_file)
            sheets = xls.sheet_names
            
            # 创建一个字典来存储每个表的数据
            all_sheets = {}
            for sheet in sheets:
                all_sheets[sheet] = pd.read_excel(target_file, sheet_name=sheet)
                print(f"成功读取目标文件的'{sheet}'表，共 {len(all_sheets[sheet])} 行")
        except Exception as e:
            print(f"读取目标文件时出错: {e}")
            print("将创建新的工作表")
            all_sheets = {
                '总': pd.DataFrame(),
                '开屏': pd.DataFrame()
            }
        
        # 创建要追加的新数据
        if not pivot1.empty:
            # 为"总"表准备数据
            append_df_total = pivot1.copy()
            
            # 将日期格式修改为 yyyy/m/d
            # 首先检查日期列的格式
            if '日期' in append_df_total.columns:
                try:
                    # 如果日期列已经是日期对象，转换为 yyyy/m/d 格式
                    if pd.api.types.is_datetime64_any_dtype(append_df_total['日期']):
                        append_df_total['日期'] = append_df_total['日期'].dt.strftime('%Y/%m/%d')
                    else:
                        # 尝试解析字符串日期并重新格式化
                        temp_dates = pd.to_datetime(append_df_total['日期'], errors='coerce')
                        valid_mask = ~temp_dates.isna()
                        if valid_mask.any():
                            append_df_total.loc[valid_mask, '日期'] = temp_dates[valid_mask].dt.strftime('%Y/%m/%d')
                            
                            # 对于无法解析的日期，尝试自定义解析
                            if (~valid_mask).any():
                                print("警告: 一些日期无法自动解析，尝试手动解析")
                                for idx in append_df_total.index[~valid_mask]:
                                    date_str = str(append_df_total.loc[idx, '日期'])
                                    # 尝试识别 yyyy/mm/dd 或 yyyy-mm-dd 或其他常见格式
                                    date_parts = re.findall(r'\d+', date_str)
                                    if len(date_parts) >= 3:
                                        year, month, day = date_parts[0], date_parts[1], date_parts[2]
                                        if len(year) == 4:  # 确保年份是4位数
                                            append_df_total.loc[idx, '日期'] = f"{year}/{int(month)}/{int(day)}"
                except Exception as e:
                    print(f"日期格式转换时出错: {e}")
            
            # 重命名列以匹配目标文件格式
            column_mapping = {
                '最终客户': '行标签',
                '后台实际营收(无余量)': '求和项:税后收入',
                '曝光(无余量)': '求和项:曝光'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in append_df_total.columns:
                    append_df_total.rename(columns={old_col: new_col}, inplace=True)
            
            # 确保所有必要的列都存在
            if '总' in all_sheets:
                existing_df_total = all_sheets['总']
                for col in existing_df_total.columns:
                    if col not in append_df_total.columns:
                        append_df_total[col] = None  # 添加缺失的列并填充为空
                
                # 仅保留目标文件中存在的列，并按相同顺序排列
                append_df_total = append_df_total[existing_df_total.columns]
                
                # 合并数据
                combined_df_total = pd.concat([existing_df_total, append_df_total], ignore_index=True)
                all_sheets['总'] = combined_df_total
            else:
                all_sheets['总'] = append_df_total
            
            # 如果有Splash数据，也添加到"开屏"表中
            if not pivot2.empty:
                append_df_splash = pivot2.copy()
                
                # 将日期格式修改为 yyyy/m/d
                if '日期' in append_df_splash.columns:
                    try:
                        if pd.api.types.is_datetime64_any_dtype(append_df_splash['日期']):
                            append_df_splash['日期'] = append_df_splash['日期'].dt.strftime('%Y/%m/%d')
                        else:
                            temp_dates = pd.to_datetime(append_df_splash['日期'], errors='coerce')
                            valid_mask = ~temp_dates.isna()
                            if valid_mask.any():
                                append_df_splash.loc[valid_mask, '日期'] = temp_dates[valid_mask].dt.strftime('%Y/%m/%d')
                                
                                if (~valid_mask).any():
                                    print("警告: 一些开屏数据的日期无法自动解析，尝试手动解析")
                                    for idx in append_df_splash.index[~valid_mask]:
                                        date_str = str(append_df_splash.loc[idx, '日期'])
                                        date_parts = re.findall(r'\d+', date_str)
                                        if len(date_parts) >= 3:
                                            year, month, day = date_parts[0], date_parts[1], date_parts[2]
                                            if len(year) == 4:
                                                append_df_splash.loc[idx, '日期'] = f"{year}/{int(month)}/{int(day)}"
                    except Exception as e:
                        print(f"开屏数据日期格式转换时出错: {e}")
                
                # 重命名列以匹配目标文件格式
                for old_col, new_col in column_mapping.items():
                    if old_col in append_df_splash.columns:
                        append_df_splash.rename(columns={old_col: new_col}, inplace=True)
                
                # 确保所有必要的列都存在
                if '开屏' in all_sheets:
                    existing_df_splash = all_sheets['开屏']
                    for col in existing_df_splash.columns:
                        if col not in append_df_splash.columns:
                            append_df_splash[col] = None
                    
                    # 仅保留目标文件中存在的列，并按相同顺序排列
                    append_df_splash = append_df_splash[existing_df_splash.columns]
                    
                    # 合并数据
                    combined_df_splash = pd.concat([existing_df_splash, append_df_splash], ignore_index=True)
                    all_sheets['开屏'] = combined_df_splash
                else:
                    all_sheets['开屏'] = append_df_splash
            
            # 写入Excel文件
            try:
                with pd.ExcelWriter(target_file, engine='openpyxl') as writer:
                    for sheet_name, df in all_sheets.items():
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"成功将数据更新到 '{target_file}' 的所有表")
            except Exception as e:
                print(f"写入目标文件时出错: {e}")
                
                # 如果有问题，尝试分别写入每个表
                try:
                    for sheet_name, df in all_sheets.items():
                        with pd.ExcelWriter(target_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                        print(f"已将数据写入 '{target_file}' 的'{sheet_name}'表")
                except Exception as e:
                    print(f"分别写入表时出错: {e}")
        
        return output_file
    except Exception as e:
        print(f"将数据追加到目标文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return output_file  # 仍然返回本地文件路径

if __name__ == "__main__":
    try:
        # 查找下载路径中的合同数据文件
        download_path = os.path.expanduser("~/Downloads")
        print(f"正在查找下载路径: {download_path}")
        
        contract_file = find_contract_file(download_path)
        
        if contract_file:
            result = process_contract_data(contract_file)
            if result:
                print(f"处理完成，结果保存在: {result}")
            else:
                print("处理过程中出现错误，未生成结果文件")
        else:
            # 如果下载路径没找到，尝试当前目录
            current_dir = os.getcwd()
            print(f"在下载路径未找到合同数据文件，尝试在当前目录查找: {current_dir}")
            
            contract_file = find_contract_file(current_dir)
            if contract_file:
                result = process_contract_data(contract_file)
                if result:
                    print(f"处理完成，结果保存在: {result}")
                else:
                    print("处理过程中出现错误，未生成结果文件")
            else:
                # 如果还是没找到，让用户手动输入文件路径
                print("在下载路径和当前目录都未找到合同数据文件")
                file_path = input("请手动输入合同数据CSV文件的完整路径: ")
                
                if os.path.exists(file_path) and file_path.endswith('.csv'):
                    result = process_contract_data(file_path)
                    if result:
                        print(f"处理完成，结果保存在: {result}")
                    else:
                        print("处理过程中出现错误，未生成结果文件")
                else:
                    print("文件路径无效或不是CSV文件")
    except Exception as e:
        print(f"程序执行过程中出现未处理的错误: {e}")
        import traceback
        traceback.print_exc()
