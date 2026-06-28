"""同义词词林扩展版加载器

数据格式：
  - 前约 107 行为分类目录（编码 + 类别名），以空格分隔
  - 之后为实际词条行：`编码 词1 词2 词3 ...`
  - 同一编码的词互为近义词
  - 编码第 8 位为标记：'=' 表示同义，'#' 表示相关，'*' 表示独立词

编码结构（8 位）：
  A B C D E F G 标记
  | | | | | | | |
  | | | | | | | ── = 同义 / # 相关 / * 独立
  | | | | | | └── 第 4 级
  | | | | | └──── 第 3 级
  | | | | └────── 第 2 级
  | | | └──────── 词类小类
  | | └────────── 词类中类
  | └──────────── 词类大类
  └────────────── 大类（A-L）
"""

from pathlib import Path
from typing import Optional

# 词林数据默认路径
_DEFAULT_DATA_PATH = Path(__file__).parent.parent / "data" / "cilin.txt"


class CilinLoader:
    """同义词词林加载器，构建 word → {code, synonyms, antonyms} 索引"""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or _DEFAULT_DATA_PATH
        # word → set of codes
        self._word_codes: dict[str, set[str]] = {}
        # code → list of words
        self._code_words: dict[str, list[str]] = {}
        # code → marker ('=', '#', '*')
        self._code_marker: dict[str, str] = {}
        # 反义词对（手动补充 + 词林规则推导）
        self._antonym_pairs: dict[str, set[str]] = {}
        self._loaded = False

    def load(self) -> None:
        """加载词林数据，构建索引"""
        if self._loaded:
            return

        # 词林文件可能是 GBK 或 UTF-8 编码，优先尝试 UTF-8，失败则回退 GBK
        try:
            f = open(self.data_path, "r", encoding="utf-8")
            f.readline()  # 测试读取
            f.seek(0)
        except UnicodeDecodeError:
            f = open(self.data_path, "r", encoding="gbk")

        with f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue

                code = parts[0]
                words = parts[1:]

                # 跳过分类目录行（编码无标记位且 words 只有 1 个且是中文类别名）
                # 实际词条行的编码长度 >= 5 且最后一位是 =/#/*
                if len(code) < 5:
                    continue

                # 提取标记位
                marker = code[-1] if code[-1] in ("=", "#", "*") else ""
                if marker:
                    code_base = code[:-1]
                else:
                    code_base = code
                    marker = "="  # 默认视为同义

                self._code_words.setdefault(code, []).extend(words)
                self._code_marker[code] = marker

                for w in words:
                    self._word_codes.setdefault(w, set()).add(code)

        # 构建反义词索引
        self._build_antonyms()

        self._loaded = True

    def _build_antonyms(self) -> None:
        """构建反义词索引

        词林本身不直接提供反义词，但可以通过以下方式推导：
        1. 手动补充常见反义词对
        2. 同一大类下不同小类的对立关系（如大/小、高/低、多/少）
        """
        # 手动补充的常见反义词对
        manual_antonyms = [
            # 体积/大小
            ("大", "小"), ("巨大", "微小"), ("庞大", "渺小"),
            ("宽", "窄"), ("宽阔", "狭窄"), ("广阔", "狭小"),
            ("粗", "细"), ("厚", "薄"),
            # 高低/长短
            ("高", "低"), ("高", "矮"), ("高大", "矮小"),
            ("长", "短"), ("深", "浅"),
            # 多少/轻重
            ("多", "少"), ("重", "轻"),
            # 快慢
            ("快", "慢"), ("快速", "缓慢"), ("迅速", "迟缓"),
            # 方向
            ("上", "下"), ("左", "右"), ("前", "后"), ("内", "外"),
            ("东", "西"), ("南", "北"),
            ("进", "退"), ("升", "降"), ("升", "落"),
            # 程度
            ("强", "弱"), ("好", "坏"), ("优", "劣"),
            ("新", "旧"), ("老", "少"), ("老", "新"),
            ("真", "假"), ("对", "错"),
            # 温度
            ("热", "冷"), ("热", "凉"), ("温暖", "寒冷"),
            ("热", "寒"),
            # 明暗/颜色
            ("明", "暗"), ("亮", "暗"), ("明亮", "黑暗"),
            ("白", "黑"),
            # 情感
            ("喜", "悲"), ("笑", "哭"), ("乐", "悲"),
            ("爱", "恨"), ("喜欢", "讨厌"), ("喜欢", "厌恶"),
            ("高兴", "难过"), ("快乐", "悲伤"), ("快乐", "痛苦"),
            ("热情", "冷漠"), ("积极", "消极"),
            # 动作
            ("开", "关"), ("来", "去"), ("起", "落"),
            ("买", "卖"), ("得", "失"), ("成", "败"),
            ("生", "死"), ("聚", "散"),
            # 状态
            ("动", "静"), ("忙", "闲"), ("紧", "松"),
            ("湿", "干"), ("软", "硬"), ("钝", "锋利"),
            ("满", "空"),
            # 其他
            ("是", "非"), ("有", "无"), ("加", "减"),
            ("正", "反"), ("公", "私"), ("虚", "实"),
            ("贵", "贱"), ("富", "穷"), ("富", "贫"),
            ("安全", "危险"), ("简单", "复杂"),
            ("容易", "困难"), ("清楚", "模糊"),
            ("整齐", "杂乱"), ("安静", "吵闹"),
            ("成功", "失败"), ("胜利", "失败"),
            ("增加", "减少"), ("上升", "下降"),
            ("建设", "破坏"), ("团结", "分裂"),
            ("奖励", "惩罚"), ("优点", "缺点"),
        ]

        for w1, w2 in manual_antonyms:
            self._antonym_pairs.setdefault(w1, set()).add(w2)
            self._antonym_pairs.setdefault(w2, set()).add(w1)

    def get_synonyms(self, word: str) -> list[str]:
        """获取词语的近义词列表"""
        if not self._loaded:
            self.load()

        codes = self._word_codes.get(word)
        if not codes:
            return []

        result: list[str] = []
        seen: set[str] = {word}
        for code in codes:
            marker = self._code_marker.get(code, "")
            # 只有同义标记 '=' 的才是近义词
            if marker in ("=", ""):
                for w in self._code_words.get(code, []):
                    if w not in seen:
                        result.append(w)
                        seen.add(w)
        return result

    def get_antonyms(self, word: str) -> list[str]:
        """获取词语的反义词列表"""
        if not self._loaded:
            self.load()

        return list(self._antonym_pairs.get(word, set()))

    def is_similar(self, word1: str, word2: str) -> bool:
        """判断两个词语是否近义

        判断规则（按优先级）：
        1. 完全相同 → True
        2. 一个包含另一个（如"自然风光"包含"自然"）→ True
        3. 共享同一词林编码（同义标记）→ True
        4. 词林近义关系（一方在另一方的近义词列表中）→ True
        5. 共享前缀（>=2 字符）→ True（如"自然风光"和"自然景观"共享"自然"）
        6. 共享核心词（最长公共子串 >=2 且在两者开头）→ True
        7. 字符重叠度 > 0.5 → True
        """
        if not self._loaded:
            self.load()

        # 1. 完全相同
        if word1 == word2:
            return True

        # 2. 包含关系
        if word1 in word2 or word2 in word1:
            return True

        # 3. 共享词林编码
        codes1 = self._word_codes.get(word1, set())
        codes2 = self._word_codes.get(word2, set())
        if codes1 and codes2:
            shared = codes1 & codes2
            if shared:
                for code in shared:
                    if self._code_marker.get(code, "") in ("=", ""):
                        return True

        # 4. 词林近义关系
        syns1 = self.get_synonyms(word1)
        if word2 in syns1:
            return True
        syns2 = self.get_synonyms(word2)
        if word1 in syns2:
            return True

        # 5. 共享前缀检测（>=2 字符）
        prefix_len = 0
        for c1, c2 in zip(word1, word2):
            if c1 == c2:
                prefix_len += 1
            else:
                break
        if prefix_len >= 2:
            return True

        # 6. 共享核心词检测：最长公共子串 >=2 且至少一方以此开头
        common = self._longest_common_substr(word1, word2)
        if len(common) >= 2:
            if word1.startswith(common) or word2.startswith(common):
                return True

        # 7. 字符重叠度 > 0.5
        if self._char_overlap(word1, word2) > 0.5:
            return True

        return False

    def deduplicate_options(self, options: list[str]) -> list[str]:
        """批量去重：移除列表中语义近似的选项，保留首次出现的

        Args:
            options: 待去重的选项列表

        Returns:
            去重后的选项列表
        """
        if not self._loaded:
            self.load()

        result: list[str] = []
        for opt in options:
            is_dup = False
            for kept in result:
                if self.is_similar(opt, kept):
                    is_dup = True
                    break
            if not is_dup:
                result.append(opt)
        return result

    @staticmethod
    def _char_overlap(s1: str, s2: str) -> float:
        """计算两个字符串的字符重叠度（0~1）"""
        if not s1 or not s2:
            return 0.0
        set1 = set(s1)
        set2 = set(s2)
        intersection = set1 & set2
        denominator = min(len(set1), len(set2))
        return len(intersection) / denominator if denominator > 0 else 0.0

    @staticmethod
    def _longest_common_substr(s1: str, s2: str) -> str:
        """求两个字符串的最长公共子串"""
        if not s1 or not s2:
            return ""
        m, n = len(s1), len(s2)
        # dp[i][j] = 以 s1[i-1] 和 s2[j-1] 结尾的最长公共子串长度
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        max_len = 0
        max_end = 0  # s1 中的结束位置
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i - 1] == s2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                    if dp[i][j] > max_len:
                        max_len = dp[i][j]
                        max_end = i
        return s1[max_end - max_len:max_end] if max_len > 0 else ""

    @property
    def word_count(self) -> int:
        """已索引的词语总数"""
        if not self._loaded:
            self.load()
        return len(self._word_codes)

    @property
    def code_count(self) -> int:
        """编码总数"""
        if not self._loaded:
            self.load()
        return len(self._code_words)


# 全局单例
_loader_instance: Optional[CilinLoader] = None


def get_loader() -> CilinLoader:
    """获取词林加载器单例"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = CilinLoader()
        _loader_instance.load()
    return _loader_instance
