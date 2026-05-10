import re

def parse_clk_tree(filepath):
    tree = {}
    tree["root"] = None
    tree["nodes"] = {}
    
    with open(filepath) as f:
        for line in f:
            line = line.rstrip()
            m = re.match(r"Root: (\S+)", line)
            if m:
                tree["root"] = m.group(1)
                continue
            m = re.match(r"\s+\[(\d+)\] (\S+) \((\S+)\)(.*)", line)
            if m:
                level = int(m.group(1))
                name = m.group(2)
                cell_type = m.group(3)
                is_sink = "SINK" in m.group(4)
                tree["nodes"][name] = {
                    "level": level,
                    "cell_type": cell_type,
                    "is_sink": is_sink,
                    "children": []
                }
    return tree

def parse_buf_lib(filepath):
    lib = {}
    current_cell = None
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            m = re.match(r"cell \((\S+)\)", line)
            if m:
                current_cell = m.group(1)
                lib[current_cell] = {}
                continue
            if current_cell:
                m = re.match(r"SIZE ([\.\d]+) BY ([\.\d]+)", line)
                if m:
                    lib[current_cell]["area"] = float(m.group(1)) * float(m.group(2))
                m = re.match(r"SS_DELAY (.+)", line)
                if m:
                    lib[current_cell]["ss_delay"] = [float(x) for x in m.group(1).split()]
                m = re.match(r"FF_DELAY (.+)", line)
                if m:
                    lib[current_cell]["ff_delay"] = [float(x) for x in m.group(1).split()]
    return lib

def parse_delay_rpt(filepath):
    result = {"clock_period": None, "paths": {}}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            m = re.match(r"Clock Period : ([\.\d]+)", line)
            if m:
                result["clock_period"] = float(m.group(1))
            m = re.match(r"(\S+) : (\S+) -> (\S+) ([\.\d]+)", line)
            if m:
                path_name = m.group(1)
                launch = m.group(2)
                capture = m.group(3)
                delay = float(m.group(4))
                result["paths"][path_name] = {
                    "launch": launch,
                    "capture": capture,
                    "delay": delay
                }
    return result

if __name__ == "__main__":
    import sys
    testcase_dir = sys.argv[1] if len(sys.argv) > 1 else "testcase0"
    
    tree = parse_clk_tree(f"{testcase_dir}/clk_tree.structure")
    lib = parse_buf_lib(f"{testcase_dir}/buf.lib")
    ss = parse_delay_rpt(f"{testcase_dir}/SS_delay.rpt")
    ff = parse_delay_rpt(f"{testcase_dir}/FF_delay.rpt")
    
    print(f"Root: {tree["root"]}")
    print(f"Nodes: {len(tree["nodes"])}")
    print(f"Buffers in lib: {list(lib.keys())}")
    print(f"Clock Period: {ss["clock_period"]}")
    print(f"Paths: {list(ss["paths"].keys())}")
