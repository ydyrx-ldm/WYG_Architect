"""MCP 工具实现：近义词/反义词/相似度/去重"""

from typing import Any
from loaders.cilin_loader import get_loader


async def get_synonyms(word: str) -> dict[str, Any]:
    """获取词语的近义词列表

    Args:
        word: 要查询的词语

    Returns:
        {"word": word, "synonyms": [...], "count": N}
    """
    loader = get_loader()
    synonyms = loader.get_synonyms(word)
    return {
        "word": word,
        "synonyms": synonyms,
        "count": len(synonyms),
    }


async def get_antonyms(word: str) -> dict[str, Any]:
    """获取词语的反义词列表

    Args:
        word: 要查询的词语

    Returns:
        {"word": word, "antonyms": [...], "count": N}
    """
    loader = get_loader()
    antonyms = loader.get_antonyms(word)
    return {
        "word": word,
        "antonyms": antonyms,
        "count": len(antonyms),
    }


async def is_similar(word1: str, word2: str) -> dict[str, Any]:
    """判断两个词语是否近义

    Args:
        word1: 词语1
        word2: 词语2

    Returns:
        {"word1": word1, "word2": word2, "similar": bool, "reason": str}
    """
    loader = get_loader()

    # 记录判断原因
    reason = ""
    if word1 == word2:
        similar = True
        reason = "完全相同"
    elif word1 in word2 or word2 in word1:
        similar = True
        reason = "包含关系"
    else:
        similar = loader.is_similar(word1, word2)
        if similar:
            # 尝试确定原因
            codes1 = loader._word_codes.get(word1, set())
            codes2 = loader._word_codes.get(word2, set())
            if codes1 and codes2 and (codes1 & codes2):
                reason = f"共享词林编码: {codes1 & codes2}"
            elif loader._char_overlap(word1, word2) > 0.5:
                reason = f"字符重叠度: {loader._char_overlap(word1, word2):.2f}"
            else:
                reason = "词林近义关系"
        else:
            reason = "无近义关系"

    return {
        "word1": word1,
        "word2": word2,
        "similar": similar,
        "reason": reason,
    }


async def deduplicate_options(options: list[str]) -> dict[str, Any]:
    """批量去重：移除列表中语义近似的选项

    Args:
        options: 待去重的选项列表

    Returns:
        {"original": [...], "deduplicated": [...], "removed": [...],
         "original_count": N, "deduplicated_count": M}
    """
    loader = get_loader()
    deduped = loader.deduplicate_options(options)

    removed = [opt for opt in options if opt not in deduped]

    return {
        "original": options,
        "deduplicated": deduped,
        "removed": removed,
        "original_count": len(options),
        "deduplicated_count": len(deduped),
    }
