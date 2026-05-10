import sys
sys.path.insert(0, ".")
from parser import parse_clk_tree, parse_buf_lib, parse_delay_rpt
from optimizer import ClockTree, optimize
from writer import write_clk_tree

def main():
    if len(sys.argv) < 3:
        print("Usage: ./cadd0000 <testcase_dir> <output_path>")
        sys.exit(1)

    testcase_dir = sys.argv[1]
    output_path = sys.argv[2]
    input_path = f"{testcase_dir}/clk_tree.structure"

    raw_tree = parse_clk_tree(input_path)
    lib = parse_buf_lib(f"{testcase_dir}/buf.lib")
    ss = parse_delay_rpt(f"{testcase_dir}/SS_delay.rpt")
    ff = parse_delay_rpt(f"{testcase_dir}/FF_delay.rpt")

    ct = ClockTree(raw_tree, lib)
    optimize(ct, ss, ff)
    write_clk_tree(ct, input_path, output_path)

if __name__ == "__main__":
    main()
