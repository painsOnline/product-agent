"""
解题思路（这里我没用高级写法，便于一眼看出解题思路）：
将字符串拆分为数组 按换行拆分
将拆分的数组再按空格拆分
然后用一个字典分类统计
最后输出结果
"""
if __name__ == "__main__":
    input_str = "普通硅酸盐水泥 50\n白水泥 30\n普通硅酸盐水泥 20"
    input_arr = input_str.split("\n")
    count_map = dict()
    for input_str in input_arr:
        count_arr = input_str.split(" ")
        count_key = count_arr[0]
        count_value = count_arr[1]
        if count_key in count_map:
            count_map[count_key] += int(count_value)
        else:
            count_map[count_key] = int(count_value)
    for key, value in count_map.items():
        print(f"产品: {key}, 统计: {value}")