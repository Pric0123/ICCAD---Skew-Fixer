import sys
sys.path.insert(0, ".")
from parser import parse_clk_tree, parse_buf_lib, parse_delay_rpt


def get_buf_delay(lib, cell_type, fanout, corner="ss"):
    if cell_type not in lib:
        return 0.0
    key = "ss_delay" if corner == "ss" else "ff_delay"
    delays = lib[cell_type][key]
    idx = min(fanout - 1, len(delays) - 1)
    return delays[idx]


def build_parent_map(tree):
    """建立每個節點的 parent 對應表"""
    nodes = tree["nodes"]
    parent_map = {}
    node_list = list(nodes.items())

    for i, (name, node) in enumerate(node_list):
        level = node["level"]
        # 找最近的上層節點作為 parent
        for j in range(i - 1, -1, -1):
            pname, pnode = node_list[j]
            if pnode["level"] == level - 1 and not pnode["is_sink"]:
                parent_map[name] = pname
                break

    return parent_map


def compute_clk_delay(tree, lib, ff_name, corner="ss"):
    """計算從 root 到指定 FF 的 clock delay"""
    nodes = tree["nodes"]
    parent_map = build_parent_map(tree)

    total_delay = 0.0
    current = ff_name

    # 往上追到 root
    path = []
    while current in parent_map:
        current = parent_map[current]
        path.append(current)

    # 計算路徑上每個 buffer 的 delay
    for node_name in path:
        node = nodes[node_name]
        cell_type = node["cell_type"]
        # 計算這個 buffer 的 fanout
        fanout = sum(1 for n, nd in nodes.items()
                     if parent_map.get(n) == node_name)
        fanout = max(fanout, 1)
        total_delay += get_buf_delay(lib, cell_type, fanout, corner)

    return total_delay


def compute_slack(tree, lib, ss_data, ff_data):
    Tclk = ss_data["clock_period"]
    Tsetup = 0.08 * Tclk
    Thold = 0.05 * Tclk

    results = []

    for path_name, path_info in ss_data["paths"].items():
        launch_ff = path_info["launch"]
        capture_ff = path_info["capture"]
        Ddata_ss = path_info["delay"]
        Ddata_ff = ff_data["paths"][path_name]["delay"]

        # SS corner: setup check
        Dclk_launch_ss = compute_clk_delay(tree, lib, launch_ff, "ss")
        Dclk_capture_ss = compute_clk_delay(tree, lib, capture_ff, "ss")
        skew_ss = Dclk_capture_ss - Dclk_launch_ss
        slack_setup = Tclk - Tsetup - Ddata_ss + skew_ss

        # FF corner: hold check
        Dclk_launch_ff = compute_clk_delay(tree, lib, launch_ff, "ff")
        Dclk_capture_ff = compute_clk_delay(tree, lib, capture_ff, "ff")
        skew_ff = Dclk_capture_ff - Dclk_launch_ff
        slack_hold = Ddata_ff - Thold - skew_ff

        results.append({
            "path": path_name,
            "launch": launch_ff,
            "capture": capture_ff,
            "slack_setup": slack_setup,
            "slack_hold": slack_hold,
            "skew_ss": skew_ss,
            "skew_ff": skew_ff,
            "Ddata_ss": Ddata_ss,
            "Ddata_ff": Ddata_ff,
        })

    return results, Tclk, Tsetup, Thold


if __name__ == "__main__":
    testcase_dir = sys.argv[1] if len(sys.argv) > 1 else "testcase0"
    tree = parse_clk_tree(f"{testcase_dir}/clk_tree.structure")
    lib = parse_buf_lib(f"{testcase_dir}/buf.lib")
    ss = parse_delay_rpt(f"{testcase_dir}/SS_delay.rpt")
    ff = parse_delay_rpt(f"{testcase_dir}/FF_delay.rpt")

    results, Tclk, Tsetup, Thold = compute_slack(tree, lib, ss, ff)

    print(f"Tclk   = {Tclk}")
    print(f"Tsetup = {Tsetup:.4f}")
    print(f"Thold  = {Thold:.4f}")
    print()

    tns_setup = sum(min(r["slack_setup"], 0) for r in results)
    wns_setup = min(r["slack_setup"] for r in results)
    tns_hold = sum(min(r["slack_hold"], 0) for r in results)
    wns_hold = min(r["slack_hold"] for r in results)

    for r in results:
        status_setup = "VIOLATED" if r["slack_setup"] < 0 else "MET"
        status_hold = "VIOLATED" if r["slack_hold"] < 0 else "MET"
        print(f"{r['path']}: {r['launch']} -> {r['capture']}")
        print(f"  Setup slack: {r['slack_setup']:.4f} ({status_setup})")
        print(f"  Hold  slack: {r['slack_hold']:.4f} ({status_hold})")
        print()

    print(f"TNS setup = {tns_setup:.4f}  WNS setup = {wns_setup:.4f}")
    print(f"TNS hold  = {tns_hold:.4f}  WNS hold  = {wns_hold:.4f}")
