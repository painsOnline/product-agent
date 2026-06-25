"""
解题思路：
这个可以用正则也可以用算法实现
由于公司要求不要用AI，我大脑也记不住那些正则策略，现在我就用纯算法实现
这里说仅包含字符串()[]{}，还要成对出现，那解析为算法就是将字符串切割为数组，开始字符串必须和闭合字符串成对出现
然后有个规则就是规定每对的开始和结束字符串，即 (为开始， )为结束，依次类推
然后还有个规则就是中间不能嵌套，比如([)]这种，所谓嵌套就翻译为程序语言就是闭合区间内出现的字符也必须闭合
"""

if __name__ == "__main__":

    def is_valid(input_str: str) -> bool:
        input_arr = list(input_str)
        match_map = {")": "(", "]": "[", "}": "{"}
        match_arr = []
        for char in input_arr:
            if char not in match_map:
                match_arr.append(char)
            else:
                if not match_arr or match_arr.pop() != match_map[char]:
                    return False
        return len(match_arr) == 0


    test_str = "([)]"
    print(is_valid(test_str))  # True