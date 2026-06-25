"""
解题思路：
将字符串拆分为数组
然后做一个有序字典
字典key是输入字符串，value是统计值
然后遍历输入，key出现过的count +1 ，否则为1
最后输出字典中第一个value是1的key
"""

from collections  import OrderedDict

if __name__ == "__main__":
    result_dict = OrderedDict()
    input_str = "A1 B2 A1 C3 B2"
    input_arr = input_str.split()
    for input_str in input_arr:
        key = input_str
        if key in result_dict:
            result_dict[key] += 1
        else:
            result_dict[key] = 1
    for key, value in result_dict.items():
        if value == 1:
            print(key)
            break
