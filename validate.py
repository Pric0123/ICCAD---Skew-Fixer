#!/usr/bin/env python3
"""
驗證 modified_clk_tree.structure 的合規性
用法: python3 validate.py <testcase_dir> <modified_clk_tree.structure>
"""
import sys
import re
sys.path.insert(0, ".")
from parser import parse_clk_tree, parse_buf_lib


def validate(original_path, modified_path, lib_path):
    errors = []
    warnings = []

    orig = parse_clk_tree(original_path)
    mod = parse_clk_tree(modified_path)
    lib = parse_buf_lib(lib_path)

    orig_nodes = orig["nodes"]
    mod_nodes = mod["nodes"]

    # 1. Root 名稱不變
    if orig["root"] != mod["root"]:
        errors.append(f"Root 名稱改變: {orig['root']} → {mod['root']}")

    # 2. 既有元件不得刪除或改名
    for name in orig_nodes:
        if name not in mod_nodes:
            errors.append(f"既有元件消失: {name}")

    # 3. 既有元件 cell_type 只允許被 resize（在 lib 裡的型號）
    for name in orig_nodes:
        if name in mod_nodes:
            new_type = mod_nodes[name]["cell_type"]
            if orig_nodes[name]["is_sink"]:
                continue
            if new_type not in lib:
                errors.append(f"{name} 的 cell_type '{new_type}' 不在 lib 裡")

    # 4. 新增 buffer 命名規則：NEW_BUF_X，X 從 0 開始連續不重複
    new_bufs = [n for n in mod_nodes if n not in orig_nodes]
    for name in new_bufs:
        if not re.match(r"^NEW_BUF_\d+$", name):
            errors.append(f"新 buffer 命名不合規: {name}")

    new_buf_indices = []
    for name in new_bufs:
        m = re.match(r"^NEW_BUF_(\d+)$", name)
        if m:
            new_buf_indices.append(int(m.group(1)))
    new_buf_indices.sort()
    for i, idx in enumerate(new_buf_indices):
        if idx != i:
            errors.append(f"NEW_BUF 編號不連續: 預期 {i} 但得到 {idx}")

    # 5. 既有元件前後順序不變
    orig_order = [n for n in orig_nodes]
    mod_orig_order = [n for n in mod_nodes if n in orig_nodes]
    if orig_order != mod_orig_order:
        errors.append(f"既有元件順序改變")
        errors.append(f"  原始: {orig_order}")
        errors.append(f"  修改: {mod_orig_order}")

    # 6. fanout 不超過 lib 限制
    # 建立 parent map
    parent_map = {}
    node_list = list(mod_nodes.items())
    for i, (name, node) in enumerate(node_list):
        level = node["level"]
        for j in range(i - 1, -1, -1):
            pname, pnode = node_list[j]
            if pnode["level"] == level - 1 and not pnode["is_sink"]:
                parent_map[name] = pname
                break

    fanout_map = {}
    for name in mod_nodes:
        parent = parent_map.get(name)
        if parent:
            fanout_map[parent] = fanout_map.get(parent, 0) + 1

    for name, node in mod_nodes.items():
        if node["is_sink"]:
            continue
        cell_type = node["cell_type"]
        if cell_type not in lib:
            continue
        fanout = fanout_map.get(name, 0)
        max_fanout = min(len(lib[cell_type]["ss_delay"]), len(lib[cell_type]["ff_delay"]))
        if fanout > max_fanout:
            errors.append(f"{name} ({cell_type}) fanout={fanout} 超過限制 {max_fanout}")

    # 7. FF 只被單一 buffer 驅動（fanout 不重複驅動同一 FF）
    for name, node in mod_nodes.items():
        if node["is_sink"]:
            drivers = [p for p, c in fanout_map.items() if name in [
                n for n in mod_nodes if parent_map.get(n) == p
            ]]

    # 8. 新 buffer 不是 sink
    for name in new_bufs:
        if mod_nodes[name]["is_sink"]:
            errors.append(f"新 buffer {name} 被標記為 SINK")

    # 輸出結果
    print(f"驗證: {modified_path}")
    print(f"既有節點: {len(orig_nodes)}  修改後總節點: {len(mod_nodes)}  新增: {len(new_bufs)}")
    print()

    if errors:
        print(f"❌ 發現 {len(errors)} 個錯誤:")
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("✅ 格式驗證通過")

    if warnings:
        for w in warnings:
            print(f"  WARN: {w}")

    return len(errors) == 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 validate.py <testcase_dir> <modified_clk_tree.structure>")
        sys.exit(1)

    testcase_dir = sys.argv[1]
    modified_path = sys.argv[2]
    original_path = f"{testcase_dir}/clk_tree.structure"
    lib_path = f"{testcase_dir}/buf.lib"

    ok = validate(original_path, modified_path, lib_path)
    sys.exit(0 if ok else 1)
