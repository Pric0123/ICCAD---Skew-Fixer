import sys
import re
sys.path.insert(0, ".")
from parser import parse_clk_tree, parse_buf_lib, parse_delay_rpt
from optimizer import ClockTree, optimize


def write_clk_tree(ct, input_path, output_path):
    with open(input_path, "r") as f:
        original_lines = f.readlines()

    # 找出所有新插入的 buffer，建立 before -> [new_buf_names] 的對應
    insert_before = {}
    for name, node in ct.nodes.items():
        if not node.get("original", True):
            if node["children"]:
                before = node["children"][0]
                if before not in insert_before:
                    insert_before[before] = []
                insert_before[before].append(name)

    output_lines = []
    for line in original_lines:
        stripped = line.rstrip()
        if not stripped:
            continue

        if stripped.startswith("Root:"):
            output_lines.append(stripped)
            continue

        m = re.match(r"\s*\[(\d+)\]\s+(\S+)\s+\((\S+)\)(.*)", stripped)
        if not m:
            continue

        level = int(m.group(1))
        node_name = m.group(2)
        cell_type = m.group(3)
        rest = m.group(4).strip()
        sink_str = " (SINK)" if "SINK" in rest else ""

        if node_name in insert_before:
            for new_buf_name in insert_before[node_name]:
                new_buf_type = ct.nodes[new_buf_name]["cell_type"]
                output_lines.append(f" [{level}] {new_buf_name} ({new_buf_type})")
            level += 1

        output_lines.append(f" [{level}] {node_name} ({cell_type}){sink_str}")

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
