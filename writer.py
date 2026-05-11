import sys
import re
sys.path.insert(0, ".")
from parser import parse_clk_tree, parse_buf_lib, parse_delay_rpt
from optimizer import ClockTree, optimize


def write_clk_tree(ct, input_path, output_path):
    with open(input_path, "r") as f:
        original_lines = f.readlines()

    # 對每個原始節點，找出插在它正上方的新 buffer 鏈
    # 新 buffer 的 children[0] 可能是另一個新 buffer，最終才接到原始節點
    # 所以要從原始節點往上追，收集所有新 buffer 直到碰到原始節點的 parent

    def get_new_buf_chain(original_node_name):
        """
        從 original_node_name 往上追，
        收集插在它上方的所有新 buffer（按從上到下順序）
        """
        chain = []
        current = ct.nodes[original_node_name]["parent"]
        while current is not None and not ct.nodes[current].get("original", True):
            chain.append(current)
            current = ct.nodes[current]["parent"]
        chain.reverse()  # 由上到下
        return chain

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

        # 取得插在這個節點上方的新 buffer 鏈
        chain = get_new_buf_chain(node_name)

        if chain:
            for i, buf_name in enumerate(chain):
                buf_type = ct.nodes[buf_name]["cell_type"]
                output_lines.append(f" [{level + i}] {buf_name} ({buf_type})")
            level += len(chain)

        # 如果 cell_type 被 resize 過，用新的
        current_type = ct.nodes[node_name]["cell_type"]
        output_lines.append(f" [{level}] {node_name} ({current_type}){sink_str}")

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
