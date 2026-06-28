"""中文近义反义词典 MCP Server

提供 4 个工具：
  - get_synonyms: 查询近义词
  - get_antonyms: 查询反义词
  - is_similar: 判断两词是否近义
  - deduplicate_options: 批量去重选项
"""

import sys
import json
from pathlib import Path

# 确保项目根目录在 sys.path 中
_PROJECT_ROOT = Path(__file__).parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from tools.dict_tools import (
    get_synonyms as _get_synonyms,
    get_antonyms as _get_antonyms,
    is_similar as _is_similar,
    deduplicate_options as _deduplicate_options,
)

# 创建 MCP Server
mcp = FastMCP("chinese-dict")


@mcp.tool()
async def get_synonyms(word: str) -> str:
    """获取词语的近义词列表

    Args:
        word: 要查询的词语

    Returns:
        JSON 格式的近义词列表
    """
    result = await _get_synonyms(word)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def get_antonyms(word: str) -> str:
    """获取词语的反义词列表

    Args:
        word: 要查询的词语

    Returns:
        JSON 格式的反义词列表
    """
    result = await _get_antonyms(word)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def is_similar(word1: str, word2: str) -> str:
    """判断两个词语是否近义

    Args:
        word1: 词语1
        word2: 词语2

    Returns:
        JSON 格式的判断结果，包含 similar (bool) 和 reason (str)
    """
    result = await _is_similar(word1, word2)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def deduplicate_options(options: list[str]) -> str:
    """批量去重：移除列表中语义近似的选项

    Args:
        options: 待去重的选项列表

    Returns:
        JSON 格式的去重结果，包含 deduplicated (去重后列表) 和 removed (被移除的列表)
    """
    result = await _deduplicate_options(options)
    return json.dumps(result, ensure_ascii=False)


def main():
    """MCP Server 入口"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
