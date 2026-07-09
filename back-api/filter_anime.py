import pandas as pd

# 1. 读取文件：指定GBK编码，解决中文解码错误
file_path = "anime.csv"  # 换成你的文件实际路径
df = pd.read_csv(file_path, encoding="gbk")

# 2. 清理列名：去除首尾空格，避免列名带空格导致匹配失败
df.columns = df.columns.str.strip()

# 3. 校验年份列是否存在，避免再次出现KeyError
if "年份" not in df.columns:
    print("❌ 错误：表格中未找到【年份】列，请检查文件！")
    exit()

# 4. 提取年份数值：从"2008/3/27"这类日期字符串中提取年份，转为整数
# 先把列转为datetime类型，无法转换的设为NaT
df["年份_datetime"] = pd.to_datetime(df["年份"], errors="coerce")
# 提取年份数值，转为int类型
df["年份数值"] = df["年份_datetime"].dt.year.astype("Int64")  # Int64支持空值

# 5. 保留所有有效数据，不再按年份过滤
filter_df = df[df["年份数值"].notna()].copy()

# 6. 输出结果：比如保存筛选后的文件，或打印预览
print(f"✅ 筛选完成，共保留 {len(filter_df)} 条数据")
print("\n📊 筛选结果前10行预览：")
print(filter_df[["标题", "中文标题", "年份", "年份数值"]].head(10))

# 保存筛选后的结果到新文件
filter_df.to_csv("filtered_anime.csv", encoding="gbk", index=False)
print("\n💾 筛选结果已保存到 filtered_anime.csv")
