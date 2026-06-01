import sys
sys.path.insert(0, ".")
from parser import parse_clk_tree, parse_buf_lib, parse_delay_rpt


class ClockTree:
    def __init__(self, raw_tree, lib):
        self.root = raw_tree["root"]
        self.lib = lib
        self.nodes = {}
        self._build(raw_tree)
        self.new_buf_counter = 0
        self.resize_log = []

    def _build(self, raw_tree):
        raw_nodes = raw_tree["nodes"]
        node_list = list(raw_nodes.items())

        for name, info in node_list:
            self.nodes[name] = {
                "cell_type": info["cell_type"],
                "is_sink": info["is_sink"],
                "children": [],
                "parent": None,
                "level": info["level"],
                "original": True,
            }
        level_stack = {}
        for name, info in node_list:
            level = info["level"]
            level_stack[level] = name
            parent_level = level - 1
            if parent_level in level_stack:
                pname = level_stack[parent_level]
                self.nodes[name]["parent"] = pname
                self.nodes[pname]["children"].append(name)

    def get_fanout(self, node_name):
        return len(self.nodes[node_name]["children"])

    def get_max_fanout(self, cell_type):
        if cell_type not in self.lib:
            return 999
        return min(len(self.lib[cell_type]["ss_delay"]),
                   len(self.lib[cell_type]["ff_delay"]))

    def check_fanout_ok(self, node_name, new_type=None):
        cell_type = new_type or self.nodes[node_name]["cell_type"]
        fanout = self.get_fanout(node_name)
        return fanout <= self.get_max_fanout(cell_type)

    def get_buf_delay(self, cell_type, fanout, corner="ss"):
        if cell_type not in self.lib:
            return 0.0
        key = "ss_delay" if corner == "ss" else "ff_delay"
        delays = self.lib[cell_type][key]
        idx = min(fanout - 1, len(delays) - 1)
        return delays[idx]

    def get_clk_delay(self, ff_name, corner="ss"):
        total = 0.0
        current = ff_name
        while self.nodes[current]["parent"] is not None:
            parent = self.nodes[current]["parent"]
            cell_type = self.nodes[parent]["cell_type"]
            fanout = self.get_fanout(parent)
            fanout = max(fanout, 1)
            total += self.get_buf_delay(cell_type, fanout, corner)
            current = parent
        return total

    def insert_buffer(self, buf_type, before_node):
        parent = self.nodes[before_node]["parent"]
        if parent is None:
            return None

        new_name = f"NEW_BUF_{self.new_buf_counter}"
        self.new_buf_counter += 1

        self.nodes[new_name] = {
            "cell_type": buf_type,
            "is_sink": False,
            "children": [before_node],
            "parent": parent,
            "level": self.nodes[before_node]["level"],
            "original": False,
        }

        self.nodes[parent]["children"].remove(before_node)
        self.nodes[parent]["children"].append(new_name)
        self.nodes[before_node]["parent"] = new_name
        return new_name

    def resize_buffer(self, node_name, new_type):
        """調整既有 buffer 尺寸，檢查 fanout 限制"""
        if self.nodes[node_name]["is_sink"]:
            return False
        fanout = self.get_fanout(node_name)
        if fanout > self.get_max_fanout(new_type):
            return False
        old_type = self.nodes[node_name]["cell_type"]
        self.nodes[node_name]["cell_type"] = new_type
        self.resize_log.append({
            "name": node_name,
            "old_type": old_type,
            "new_type": new_type,
        })
        return True

    def compute_slack(self, ss_data, ff_data):
        Tclk = ss_data["clock_period"]
        Tsetup = 0.08 * Tclk
        Thold = 0.05 * Tclk
        results = []

        for path_name, path_info in ss_data["paths"].items():
            launch = path_info["launch"]
            capture = path_info["capture"]
            Ddata_ss = path_info["delay"]
            Ddata_ff = ff_data["paths"][path_name]["delay"]

            skew_ss = self.get_clk_delay(capture, "ss") - self.get_clk_delay(launch, "ss")
            skew_ff = self.get_clk_delay(capture, "ff") - self.get_clk_delay(launch, "ff")

            slack_setup = Tclk - Tsetup - Ddata_ss + skew_ss
            slack_hold = Ddata_ff - Thold - skew_ff

            results.append({
                "path": path_name,
                "launch": launch,
                "capture": capture,
                "slack_setup": slack_setup,
                "slack_hold": slack_hold,
            })

        return results, Tclk, Tsetup, Thold

    def compute_tns_wns(self, results):
        tns_ss = sum(min(r["slack_setup"], 0) for r in results)
        wns_ss = min(r["slack_setup"] for r in results) if results else 0
        tns_ff = sum(min(r["slack_hold"], 0) for r in results)
        wns_ff = min(r["slack_hold"] for r in results) if results else 0
        return tns_ss, wns_ss, tns_ff, wns_ff

    def compute_total_area(self):
        total = 0.0
        for name, node in self.nodes.items():
            if not node["is_sink"] and node["cell_type"] in self.lib:
                total += self.lib[node["cell_type"]]["area"]
        return total

    def get_path_buffers(self, ff_name):
        """取得從 root 到 ff_name 路徑上的所有 buffer"""
        path = []
        current = ff_name
        while self.nodes[current]["parent"] is not None:
            parent = self.nodes[current]["parent"]
            path.append(parent)
            current = parent
        return path


# ─────────────────────────────────────────
# 優化策略
# ─────────────────────────────────────────

def try_resize_for_setup(ct, path, all_slack=None):
    capture_ff = path["capture"]
    launch_ff = path["launch"]
    capture_bufs = ct.get_path_buffers(capture_ff)
    launch_bufs = set(ct.get_path_buffers(launch_ff))
    exclusive_capture = [b for b in capture_bufs if b not in launch_bufs]
    if all_slack is None:
        all_slack = {}
    best_result = None
    best_delta_ss = 0
    for buf_name in exclusive_capture:
        current_type = ct.nodes[buf_name]["cell_type"]
        fanout = max(ct.get_fanout(buf_name), 1)
        old_delay_ss = ct.get_buf_delay(current_type, fanout, "ss")
        old_delay_ff = ct.get_buf_delay(current_type, fanout, "ff")
        for new_type in ct.lib:
            if new_type == current_type:
                continue
            if fanout > ct.get_max_fanout(new_type):
                continue
            new_delay_ss = ct.get_buf_delay(new_type, fanout, "ss")
            new_delay_ff = ct.get_buf_delay(new_type, fanout, "ff")
            delta_ss = new_delay_ss - old_delay_ss
            delta_ff = new_delay_ff - old_delay_ff
            if delta_ss <= 0:
                continue
            safe = True
            for pname, pdata in all_slack.items():
                cap_bufs = set(ct.get_path_buffers(pdata["capture"]))
                lau_bufs = set(ct.get_path_buffers(pdata["launch"]))
                if buf_name in cap_bufs and buf_name not in lau_bufs:
                    if pdata["slack_hold"] - delta_ff < 0:
                        safe = False
                elif buf_name in lau_bufs and buf_name not in cap_bufs:
                    if pdata["slack_setup"] + delta_ss < 0:
                        safe = False
            if safe and delta_ss > best_delta_ss:
                best_delta_ss = delta_ss
                best_result = (buf_name, new_type)
    return best_result if best_result else (None, None)
def try_resize_for_hold(ct, path, all_slack=None):
    """
    在 launch 獨占路徑上找 buffer，換成 FF delay 更大的型號
    增加 launch delay → skew 變小 → hold 改善
    同時確保不破壞任何路徑的 setup slack
    """
    launch_ff = path["launch"]
    capture_ff = path["capture"]
    launch_bufs = ct.get_path_buffers(launch_ff)
    capture_bufs = set(ct.get_path_buffers(capture_ff))
    exclusive_launch = [b for b in launch_bufs if b not in capture_bufs]
    if all_slack is None:
        all_slack = {}
    best_result = None
    best_delta_ff = 0
    for buf_name in exclusive_launch:
        current_type = ct.nodes[buf_name]["cell_type"]
        fanout = max(ct.get_fanout(buf_name), 1)
        old_delay_ff = ct.get_buf_delay(current_type, fanout, "ff")
        old_delay_ss = ct.get_buf_delay(current_type, fanout, "ss")
        for new_type in ct.lib:
            if new_type == current_type:
                continue
            if fanout > ct.get_max_fanout(new_type):
                continue
            new_delay_ff = ct.get_buf_delay(new_type, fanout, "ff")
            new_delay_ss = ct.get_buf_delay(new_type, fanout, "ss")
            delta_ff = new_delay_ff - old_delay_ff
            delta_ss = new_delay_ss - old_delay_ss
            if delta_ff <= 0:
                continue
            safe = True
            for pname, pdata in all_slack.items():
                cap_bufs = set(ct.get_path_buffers(pdata["capture"]))
                lau_bufs = set(ct.get_path_buffers(pdata["launch"]))
                if buf_name in lau_bufs and buf_name not in cap_bufs:
                    if pdata["slack_setup"] + delta_ss < 0:
                        safe = False
                elif buf_name in cap_bufs and buf_name not in lau_bufs:
                    if pdata["slack_hold"] - delta_ff < 0:
                        safe = False
            if safe and delta_ff > best_delta_ff:
                best_delta_ff = delta_ff
                best_result = (buf_name, new_type)
    return best_result if best_result else (None, None)

def find_best_insert_for_setup(ct, path):
    capture_ff = path["capture"]
    best_buf = None
    best_area = float("inf")

    for buf_type, buf_info in ct.lib.items():
        delay_ss = buf_info["ss_delay"][0]
        delay_ff = buf_info["ff_delay"][0]

        new_slack_setup = path["slack_setup"] + delay_ss
        new_slack_hold = path["slack_hold"] - delay_ff

        if new_slack_hold >= 0 and buf_info["area"] < best_area:
            best_area = buf_info["area"]
            best_buf = buf_type

    return best_buf, capture_ff


def find_best_insert_for_hold(ct, path):
    """
    改良版：選 area/delay_ff 比值最小的 buffer（每單位面積 delay 效益最大）
    同時確保 setup slack 不會因此變成負的
    """
    launch_ff = path["launch"]
    best_buf = None
    best_score = float("inf")

    for buf_type, buf_info in ct.lib.items():
        delay_ff = buf_info["ff_delay"][0]
        delay_ss = buf_info["ss_delay"][0]

        new_slack_hold = path["slack_hold"] + delay_ff
        new_slack_setup = path["slack_setup"] - delay_ss

        if new_slack_setup >= 0 and delay_ff > 0:
            # 面積除以 delay 效益，越小越好
            score = buf_info["area"] / delay_ff
            if score < best_score:
                best_score = score
                best_buf = buf_type

    return best_buf, launch_ff


def optimize(ct, ss_data, ff_data, max_iterations=250):
    inserted = []
    prev_tns = float("inf")
    stall_count = 0

    for iteration in range(max_iterations):
        results, Tclk, Tsetup, Thold = ct.compute_slack(ss_data, ff_data)
        tns_ss, wns_ss, tns_ff, wns_ff = ct.compute_tns_wns(results)

        total_tns = tns_ss + tns_ff
        if total_tns >= prev_tns - 1e-6:
            stall_count += 1
        else:
            stall_count = 0
        prev_tns = total_tns
        if stall_count >= 15:
            print(f"[Iter {iteration}] TNS 連續無改善，停止")
            break
        all_slack = {r["path"]: r for r in results}
        violated_setup = [r for r in results if r["slack_setup"] < 0]
        violated_hold = [r for r in results if r["slack_hold"] < 0]

        if not violated_setup and not violated_hold:
            print(f"[Iter {iteration}] 所有路徑 MET！")
            break

        all_violated = []
        for r in violated_setup:
            all_violated.append(("setup", r["slack_setup"], r))
        for r in violated_hold:
            all_violated.append(("hold", r["slack_hold"], r))

        all_violated.sort(key=lambda x: x[1])
        vtype, vslack, vpath = all_violated[0]

        print(f"[Iter {iteration}] {vtype} violation: {vpath['path']} slack={vslack:.4f}")

        if vtype == "setup":
            resize_node, resize_type = try_resize_for_setup(ct, vpath)
            if resize_node:
                old_type = ct.nodes[resize_node]["cell_type"]
                ct.resize_buffer(resize_node, resize_type)
                print(f"  resize {resize_node}: {old_type} → {resize_type}")
                continue

            best_buf, target_ff = find_best_insert_for_setup(ct, vpath)
            if best_buf is None:
                best_buf = min(ct.lib.keys(), key=lambda x: ct.lib[x]["area"])
                target_ff = vpath["capture"]

            new_name = ct.insert_buffer(best_buf, target_ff)
            if new_name:
                inserted.append({
                    "name": new_name,
                    "type": best_buf,
                    "before": target_ff,
                    "area": ct.lib[best_buf]["area"],
                })
                print(f"  插入 {new_name} ({best_buf}) 在 {target_ff} 上方")

        else:  # hold
            resize_node, resize_type = try_resize_for_hold(ct, vpath, all_slack)
            if resize_node:
                old_type = ct.nodes[resize_node]["cell_type"]
                ct.resize_buffer(resize_node, resize_type)
                print(f"  resize {resize_node}: {old_type} → {resize_type}")
                continue
            best_buf, target_ff = find_best_insert_for_hold(ct, vpath)
            if best_buf is None:
                best_buf = min(ct.lib.keys(), key=lambda x: ct.lib[x]["area"])
                target_ff = vpath["launch"]

            new_name = ct.insert_buffer(best_buf, target_ff)
            if new_name:
                inserted.append({
                    "name": new_name,
                    "type": best_buf,
                    "before": target_ff,
                    "area": ct.lib[best_buf]["area"],
                })
                print(f"  插入 {new_name} ({best_buf}) 在 {target_ff} 上方")

    return inserted


# ─────────────────────────────────────────
# 主程式
# ─────────────────────────────────────────
if __name__ == "__main__":
    testcase_dir = sys.argv[1] if len(sys.argv) > 1 else "testcase0"

    raw_tree = parse_clk_tree(f"{testcase_dir}/clk_tree.structure")
    lib = parse_buf_lib(f"{testcase_dir}/buf.lib")
    ss = parse_delay_rpt(f"{testcase_dir}/SS_delay.rpt")
    ff = parse_delay_rpt(f"{testcase_dir}/FF_delay.rpt")

    ct = ClockTree(raw_tree, lib)

    print("=== 優化前 ===")
    results, Tclk, _, _ = ct.compute_slack(ss, ff)
    tns_ss, wns_ss, tns_ff, wns_ff = ct.compute_tns_wns(results)
    for r in results:
        s = "VIOLATED" if r["slack_setup"] < 0 else "MET"
        h = "VIOLATED" if r["slack_hold"] < 0 else "MET"
        print(f"  {r['path']}: setup={r['slack_setup']:.4f}({s}) hold={r['slack_hold']:.4f}({h})")
    print(f"SS TNS={tns_ss:.4f} WNS={wns_ss:.4f}")
    print(f"FF TNS={tns_ff:.4f} WNS={wns_ff:.4f}")
    print(f"面積={ct.compute_total_area():.4f}")
    print()

    print("=== 優化中 ===")
    inserted = optimize(ct, ss, ff)
    print()

    print("=== 優化後 ===")
    results, _, _, _ = ct.compute_slack(ss, ff)
    tns_ss, wns_ss, tns_ff, wns_ff = ct.compute_tns_wns(results)
    for r in results:
        s = "VIOLATED" if r["slack_setup"] < 0 else "MET"
        h = "VIOLATED" if r["slack_hold"] < 0 else "MET"
        print(f"  {r['path']}: setup={r['slack_setup']:.4f}({s}) hold={r['slack_hold']:.4f}({h})")
    print(f"SS TNS={tns_ss:.4f} WNS={wns_ss:.4f}")
    print(f"FF TNS={tns_ff:.4f} WNS={wns_ff:.4f}")
    print(f"面積={ct.compute_total_area():.4f}")

    if ct.resize_log:
        print()
        print("=== Resize 記錄 ===")
        for r in ct.resize_log:
            print(f"  {r['name']}: {r['old_type']} → {r['new_type']}")
