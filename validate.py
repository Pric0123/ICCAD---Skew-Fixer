#!/usr/bin/env python3
import sys, re, io
sys.path.insert(0, ".")
from parser import parse_clk_tree, parse_buf_lib, parse_delay_rpt
from optimizer import ClockTree, optimize


def validate(testcase_dir, modified_path):
    original_path = f"{testcase_dir}/clk_tree.structure"
    lib_path = f"{testcase_dir}/buf.lib"

    orig = parse_clk_tree(original_path)
    mod = parse_clk_tree(modified_path)
    lib = parse_buf_lib(lib_path)
    orig_nodes = orig["nodes"]
    mod_nodes = mod["nodes"]
    errors = []

    # 1. Root 不變
    if orig["root"] != mod["root"]:
        errors.append(f"Root 改變: {orig['root']} → {mod['root']}")

    # 2. 既有元件不得消失
    for name in orig_nodes:
        if name not in mod_nodes:
            errors.append(f"既有元件消失: {name}")

    # 3. 既有元件 cell_type 必須在 lib 裡（sink 除外）
    for name in orig_nodes:
        if name in mod_nodes and not orig_nodes[name]["is_sink"]:
            t = mod_nodes[name]["cell_type"]
            if t not in lib:
                errors.append(f"{name} cell_type '{t}' 不在 lib")

    # 4. 新 buffer 命名 NEW_BUF_X 連續
    new_bufs = [n for n in mod_nodes if n not in orig_nodes]
    for name in new_bufs:
        if not re.match(r"^NEW_BUF_\d+$", name):
            errors.append(f"新 buffer 命名不合規: {name}")
    indices = sorted([int(re.match(r"NEW_BUF_(\d+)", n).group(1)) for n in new_bufs if re.match(r"NEW_BUF_\d+", n)])
    for i, idx in enumerate(indices):
        if idx != i:
            errors.append(f"NEW_BUF 編號不連續: 預期 {i} 得到 {idx}")

    # 5. 既有元件順序不變
    orig_order = list(orig_nodes.keys())
    mod_orig_order = [n for n in mod_nodes if n in orig_nodes]
    if orig_order != mod_orig_order:
        errors.append("既有元件順序改變")

    # 6. fanout 驗證：直接對 modified tree 建 ClockTree
    ct = ClockTree({"root": mod["root"], "nodes": mod["nodes"]}, lib)

    for name, node in ct.nodes.items():
        if node["is_sink"]:
            continue
        cell_type = node["cell_type"]
        if cell_type not in lib:
            continue
        fanout = ct.get_fanout(name)
        max_fanout = min(len(lib[cell_type]["ss_delay"]), len(lib[cell_type]["ff_delay"]))
        if fanout > max_fanout:
            errors.append(f"{name} ({cell_type}) fanout={fanout} 超過限制 {max_fanout}")

    # 7. 新 buffer 不是 sink
    for name in new_bufs:
        if mod_nodes[name]["is_sink"]:
            errors.append(f"新 buffer {name} 被標記為 SINK")

    print(f"驗證: {modified_path}")
    print(f"既有節點: {len(orig_nodes)}  修改後總節點: {len(mod_nodes)}  新增: {len(new_bufs)}")
    print()
    if errors:
        print(f"❌ 發現 {len(errors)} 個錯誤:")
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("✅ 格式驗證通過")
    return len(errors) == 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 validate.py <testcase_dir> <modified_clk_tree.structure>")
        sys.exit(1)
    ok = validate(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)
