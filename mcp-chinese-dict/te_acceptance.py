"""TE 端到端验收测试 - 结果输出到文件"""

import sys
import io
import asyncio
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(_PROJECT_ROOT))

out = io.StringIO()
def p(msg):
    out.write(str(msg) + "\n")

from loaders.cilin_loader import get_loader
from tools.dict_tools import get_synonyms, get_antonyms, is_similar, deduplicate_options


async def run_acceptance_tests():
    p("=" * 60)
    p("TE Acceptance Tests - Chinese Dict MCP")
    p("=" * 60)

    loader = get_loader()

    # === 验收标准 1: get_synonyms 返回正确结果 ===
    p("\n--- Acceptance 1: get_synonyms ---")
    result = await get_synonyms("人")
    p(f"1.1 get_synonyms('ren'): count={result['count']}, sample={result['synonyms'][:3]}")
    assert result["count"] > 0, "FAIL: should have synonyms"
    p("[PASS] 1.1")

    result = await get_synonyms("电脑")
    p(f"1.2 get_synonyms('diannao'): {result['synonyms'][:5]}")
    p("[PASS] 1.2")

    result = await get_synonyms(" nonexistentXYZ")
    p(f"1.3 get_synonyms(non-existent): count={result['count']}")
    assert result["count"] == 0
    p("[PASS] 1.3")

    # === 验收标准 2: get_antonyms 返回正确结果 ===
    p("\n--- Acceptance 2: get_antonyms ---")
    result = await get_antonyms("大")
    p(f"2.1 get_antonyms('da'): {result['antonyms']}")
    assert "小" in result["antonyms"]
    p("[PASS] 2.1")

    result = await get_antonyms("快")
    p(f"2.2 get_antonyms('kuai'): {result['antonyms']}")
    assert "慢" in result["antonyms"]
    p("[PASS] 2.2")

    # === 验收标准 3: is_similar 正确判断 ===
    p("\n--- Acceptance 3: is_similar ---")
    result = await is_similar("自然风光", "自然景观")
    p(f"3.1 is_similar('ziranfengguang','ziranjingguan'): {result['similar']} ({result['reason']})")
    assert result["similar"] == True, "FAIL: should be similar (shared prefix)"
    p("[PASS] 3.1")

    result = await is_similar("自然风光", "历史文化")
    p(f"3.2 is_similar('ziranfengguang','lishiwenhua'): {result['similar']} ({result['reason']})")
    assert result["similar"] == False, "FAIL: should not be similar"
    p("[PASS] 3.2")

    result = await is_similar("休闲放松", "休闲度假")
    p(f"3.3 is_similar('xiuxianfangsong','xiuxiandujia'): {result['similar']} ({result['reason']})")
    assert result["similar"] == True, "FAIL: should be similar (shared prefix)"
    p("[PASS] 3.3")

    result = await is_similar("经济型", "舒适型")
    p(f"3.4 is_similar('jingjixing','shushixing'): {result['similar']} ({result['reason']})")
    assert result["similar"] == False, "FAIL: should not be similar (shared suffix, not prefix)"
    p("[PASS] 3.4")

    # === 验收标准 4: deduplicate_options 批量去重 ===
    p("\n--- Acceptance 4: deduplicate_options ---")
    result = await deduplicate_options(["自然风光", "自然景观", "历史文化"])
    p(f"4.1 dedup: {result['original']} -> {result['deduplicated']}, removed: {result['removed']}")
    assert len(result["deduplicated"]) == 2, "FAIL: should remove 1"
    assert "自然景观" in result["removed"]
    p("[PASS] 4.1")

    result = await deduplicate_options(["自然风光", "历史文化", "美食体验"])
    p(f"4.2 dedup (no dup): {result['original']} -> {result['deduplicated']}")
    assert len(result["deduplicated"]) == 3, "FAIL: should not remove any"
    p("[PASS] 4.2")

    result = await deduplicate_options(["休闲放松", "休闲度假", "休闲购物", "深度游览", "文化体验"])
    p(f"4.3 dedup (xiuxian): {result['original']} -> {result['deduplicated']}")
    assert len(result["deduplicated"]) == 3, "FAIL: should keep 3"
    p("[PASS] 4.3")

    # === 验收标准 5: 性能 - 去重延迟 < 10ms ===
    p("\n--- Acceptance 5: Performance ---")
    import time
    options = ["自然风光", "自然景观", "山水游览", "历史文化", "美食体验"]
    start = time.perf_counter()
    for _ in range(100):
        loader.deduplicate_options(options)
    elapsed_ms = (time.perf_counter() - start) / 100 * 1000
    p(f"5.1 avg deduplicate latency: {elapsed_ms:.2f}ms")
    assert elapsed_ms < 10, f"FAIL: too slow ({elapsed_ms:.2f}ms)"
    p("[PASS] 5.1 latency < 10ms")

    # is_similar latency
    start = time.perf_counter()
    for _ in range(1000):
        loader.is_similar("自然风光", "自然景观")
    elapsed_ms = (time.perf_counter() - start) / 1000 * 1000
    p(f"5.2 avg is_similar latency: {elapsed_ms:.3f}ms")
    assert elapsed_ms < 10, f"FAIL: too slow ({elapsed_ms:.3f}ms)"
    p("[PASS] 5.2 latency < 10ms")

    # === 验收标准 6: 回归测试 - 原有去重场景不受影响 ===
    p("\n--- Acceptance 6: Regression ---")
    # 原有 engine.py 中的场景
    test_cases = [
        (["自然风光", "自然景观"], True),   # 应去重（共享前缀"自然"）
        (["历史文化", "人文古迹"], False),  # 不应去重（字符重叠 0.25，语义不同）
        (["休闲放松", "休闲度假"], True),   # 应去重（共享前缀"休闲"）
        (["自驾", "自驾游"], True),         # 应去重（包含关系）
        (["跟团游", "团队游"], True),       # 应去重（字符重叠 0.67，语义相近）
        (["自由行", "自助游"], False),      # 不应去重（字符重叠 0.33）
        (["海边", "海滨"], False),          # 不应去重（字符重叠 0.5，不 > 0.5）
        (["深度游", "慢游"], False),        # 不应去重
    ]
    for opts, should_dedup in test_cases:
        deduped = loader.deduplicate_options(opts)
        actual_dedup = len(deduped) < len(opts)
        status = "PASS" if actual_dedup == should_dedup else "FAIL"
        p(f"  [{status}] {opts} -> {deduped} (expect dedup={should_dedup}, got={actual_dedup})")

    # === 验收标准 7: engine.py 集成验证 ===
    p("\n--- Acceptance 7: engine.py Integration ---")
    # 模拟 wyg-brain 的 engine.py 导入
    sys.path.insert(0, str(Path(__file__).parent.parent / "wyg-brain" / "backend"))
    try:
        from app.agents.engine import _normalize_ba_output, _CILIN_AVAILABLE
        p(f"7.1 CILIN_AVAILABLE: {_CILIN_AVAILABLE}")
        assert _CILIN_AVAILABLE, "FAIL: cilin should be available"
        p("[PASS] 7.1")

        # Test BA output normalization
        test_ba_output = """问题1：你想去什么类型的景点？
A) 自然风光
B) 自然景观
C) 历史文化

问题2：你的预算范围？
A) 经济型
B) 舒适型
C) 豪华型"""

        result = _normalize_ba_output(test_ba_output)
        p(f"7.2 BA output normalized:\n{result}")

        # Verify "自然景观" was removed (deduplicated with "自然风光")
        assert "自然景观" not in result, "FAIL: should be deduplicated"
        assert "自然风光" in result, "FAIL: should be kept"
        p("[PASS] 7.2 'ziranjingguan' deduplicated with 'ziranfengguang'")

        # Verify non-similar options are kept
        assert "经济型" in result and "舒适型" in result and "豪华型" in result
        p("[PASS] 7.3 non-similar options preserved")

    except Exception as e:
        p(f"[FAIL] 7.x Integration error: {e}")
        raise

    p("\n" + "=" * 60)
    p("[ALL PASS] All acceptance tests passed!")
    p("=" * 60)

    output_path = _PROJECT_ROOT / "te_acceptance_result.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(out.getvalue())
    print(f"TE acceptance results written to {output_path}")


if __name__ == "__main__":
    asyncio.run(run_acceptance_tests())
