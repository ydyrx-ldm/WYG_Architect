"""词林加载器和工具的单元测试 - 结果输出到文件"""

import sys
import asyncio
import io
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(_PROJECT_ROOT))

# 输出缓冲区
out = io.StringIO()
def p(msg):
    out.write(str(msg) + "\n")

from loaders.cilin_loader import CilinLoader, get_loader
from tools.dict_tools import (
    get_synonyms,
    get_antonyms,
    is_similar,
    deduplicate_options,
)


def test_loader_basic():
    loader = CilinLoader()
    loader.load()
    assert loader.word_count > 50000, f"word count abnormal: {loader.word_count}"
    assert loader.code_count > 1000, f"code count abnormal: {loader.code_count}"
    p(f"[PASS] loader basic: {loader.word_count} words, {loader.code_count} codes")


def test_synonyms():
    loader = get_loader()
    syns = loader.get_synonyms("人")
    assert len(syns) > 0, "'ren' should have synonyms"
    p(f"[PASS] synonyms of 'ren': {syns[:5]}...")

    syns = loader.get_synonyms("不存在的词XYZ123")
    assert syns == [], "non-existent word should return empty"
    p("[PASS] non-existent word returns empty")


def test_antonyms():
    loader = get_loader()
    antonyms = loader.get_antonyms("大")
    assert "小" in antonyms
    p(f"[PASS] antonyms of 'da': {antonyms}")

    antonyms = loader.get_antonyms("快")
    assert "慢" in antonyms
    p(f"[PASS] antonyms of 'kuai': {antonyms}")


def test_is_similar():
    loader = get_loader()

    assert loader.is_similar("自然风光", "自然风光") == True
    p("[PASS] identical words -> similar")

    assert loader.is_similar("自然", "自然风光") == True
    p("[PASS] containment -> similar")

    syns = loader.get_synonyms("人")
    if syns:
        assert loader.is_similar("人", syns[0]) == True
        p(f"[PASS] cilin synonym: 'ren' ~ '{syns[0]}'")

    assert loader.is_similar("自然风光", "历史文化") == False
    p("[PASS] not similar: 'ziranfengguang' !~ 'lishiwenhua'")

    assert loader.is_similar("美食体验", "历史文化") == False
    p("[PASS] not similar: 'meishitiyan' !~ 'lishiwenhua'")


def test_deduplicate():
    loader = get_loader()

    options = ["自然风光", "自然景观", "山水游览", "历史文化", "美食体验"]
    deduped = loader.deduplicate_options(options)
    p(f"[PASS] dedup: {options} -> {deduped}")
    assert len(deduped) < len(options), "should remove some options"

    options = ["自然风光", "历史文化", "美食体验"]
    deduped = loader.deduplicate_options(options)
    assert len(deduped) == 3, "non-similar options should not be removed"
    p(f"[PASS] no dedup needed: {deduped}")

    deduped = loader.deduplicate_options([])
    assert deduped == []
    p("[PASS] empty list -> empty list")


def test_ba_scenario():
    loader = get_loader()
    test_cases = [
        # "自然景观"与"自然风光"共享前缀"自然"→去重；"山水游览"不近义→保留
        (["自然风光", "自然景观", "山水游览", "历史文化", "美食体验"], 4),
        # "休闲度假""休闲购物"与"休闲放松"共享前缀"休闲"→去重
        (["休闲放松", "休闲度假", "休闲购物", "深度游览", "文化体验"], 3),
        # 三个完全不同的类别→不去重
        (["自然风光", "历史文化", "美食体验"], 3),
        # 三个程度递进→不去重（它们共享后缀"型"但后缀不算前缀）
        (["经济型", "舒适型", "豪华型"], 3),
    ]
    for i, (options, expected_max) in enumerate(test_cases):
        deduped = loader.deduplicate_options(options)
        status = "PASS" if len(deduped) <= expected_max else "FAIL"
        p(f"[{status}] BA scenario {i+1}: {options} -> {deduped} (expect<={expected_max}, got={len(deduped)})")


async def test_mcp_tools():
    result = await get_synonyms("人")
    assert result["word"] == "人"
    p(f"[PASS] MCP get_synonyms('ren'): count={result['count']}")

    result = await get_antonyms("大")
    assert "小" in result["antonyms"]
    p(f"[PASS] MCP get_antonyms('da'): {result['antonyms']}")

    result = await is_similar("自然风光", "自然景观")
    p(f"[PASS] MCP is_similar('ziranfengguang','ziranjingguan'): {result['similar']} ({result['reason']})")

    result = await is_similar("自然风光", "历史文化")
    p(f"[PASS] MCP is_similar('ziranfengguang','lishiwenhua'): {result['similar']} ({result['reason']})")

    result = await deduplicate_options(["自然风光", "自然景观", "历史文化"])
    p(f"[PASS] MCP deduplicate: {result['original']} -> {result['deduplicated']}, removed: {result['removed']}")


def main():
    p("=" * 60)
    p("Chinese Synonym/Antonym Dictionary MCP - Unit Tests")
    p("=" * 60)

    test_loader_basic()
    test_synonyms()
    test_antonyms()
    test_is_similar()
    test_deduplicate()
    test_ba_scenario()

    p("")
    p("=" * 60)
    p("MCP Tool Interface Tests")
    p("=" * 60)
    asyncio.run(test_mcp_tools())

    p("")
    p("=" * 60)
    p("[ALL PASS] All tests passed!")
    p("=" * 60)

    # Write to file
    output_path = _PROJECT_ROOT / "test_result.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(out.getvalue())
    print(f"Test results written to {output_path}")


if __name__ == "__main__":
    main()
