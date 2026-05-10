import sys
sys.path.insert(0, ".")
from parser import parse_clk_tree, parse_buf_lib, parse_delay_rpt
from optimizer import ClockTree, optimize


def write_clk_tree(ct, input_path, output_path):
    """
    輸出優化後的 clock tree
    格式：每行前面一個空格，不管 level 深度
    Root: ROOT_CLK
     [1] BUF_0 (REALBUF_X8)
     [2] BUF_4 (REALBUF_X4)
     [3] FF_37 (FIFO) (SINK)
    """

    # 讀原始輸入檔，取得正確的節點順序和格式
    with open(input_path, "r") as f:
        original_lines = f.readlines()

    # 建立新 buffer 的插入位置對應表
    # key: 在哪個節點上方插入, value: 新 buffer 資訊
    insert_before = {}
    for name, node in ct.nodes.items():
        if not node.get("original", True):  # 新插入的 buffer
            before = node["children"][0] if node["children"] else None
            if before:
                if before not in insert_before:
                    insert_before[before] = []
                insert_before[before].append(name)

    output_lines = []
    for line in original_lines:
        stripped = line.rstrip()

        if not stripped:
            continue

        # Root 行直接輸出
        if stripped.startswith("Root:"):
            output_lines.append(stripped)
            continue

        # 解析節點行
        import re
        m = re.match(r"\s*\[(\d+)\]\s+(\S+)\s+\((\S+)\)(.*)", stripped)
        if not m:
            continue

        level = int(m.group(1))
        node_name = m.group(2)
        cell_type = m.group(3)
        rest = m.group(4).strip()
        sink_str = " (SINK)" if "SINK" in rest else ""

        # 如果這個節點上方有新插入的 buffer，先輸出新 buffer
        if node_name in insert_before:
            for new_buf_name in insert_before[node_name]:
                new_buf_type = ct.nodes[new_buf_name]["cell_type"]
                output_lines.append(f" [{level}] {new_buf_name} ({new_buf_type})")
            # 原始節點 level + 1
            level += 1

        # 輸出原始節點
        output_lines.append(f" [{level}] {node_name} ({cell_type}){sink_str}")

    # 寫入輸出檔
    with open(output_path, "w") as f:
        f.write("\n".join(output_lines) + "\n")

    print(f"輸出至：{output_path}")


if __name__ == "__main__":
    testcase_dir = sys.argv[1] if len(sys.argv) > 1 else "testcase0"
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"{testcase_dir}/modified_clk_tree.structure"
    input_path = f"{testcase_dir}/clk_tree.structure"

    raw_tree = parse_clk_tree(input_path)
    lib = parse_buf_lib(f"{testcase_dir}/buf.lib")
    ss = parse_delay_rpt(f"{testcase_dir}/SS_delay.rpt")
    ff = parse_delay_rpt(f"{testcase_dir}/FF_delay.rpt")

    ct = ClockTree(raw_tree, lib)

    print("=== 優化中 ===")
    inserted = optimize(ct, ss, ff)
    print()

    print("=== 輸出結果 ===")
    write_clk_tree(ct, input_path, output_path)

    print()
    print("=== 輸出檔案內容 ===")
    with open(output_path) as f:
        print(f.read())

    print("=== 最終 Slack ===")
    results, _, _, _ = ct.compute_slack(ss, ff)
    tns_ss = sum(min(r["slack_setup"], 0) for r in results)
    wns_ss = min(r["slack_setup"] for r in results)
    tns_ff = sum(min(r["slack_hold"], 0) for r in results)
    wns_ff = min(r["slack_hold"] for r in results)
    print(f"SS TNS={tns_ss:.4f} WNS={wns_ss:.4f}")
    print(f"FF TNS={tns_ff:.4f} WNS={wns_ff:.4f}")
