#!/bin/bash
PASS=0
FAIL=0

run_test() {
    local tc=$1
    echo "=== $tc ==="
    python3 main.py $tc /tmp/${tc}_output.structure > /dev/null 2>&1
    result=$(python3 << PYEOF 2>/dev/null
import sys, os
sys.path.insert(0, '.')
sys.stdout = open(os.devnull, 'w')
from parser import parse_clk_tree, parse_buf_lib, parse_delay_rpt
from optimizer import ClockTree, optimize
raw_tree = parse_clk_tree('${tc}/clk_tree.structure')
lib = parse_buf_lib('${tc}/buf.lib')
ss = parse_delay_rpt('${tc}/SS_delay.rpt')
ff = parse_delay_rpt('${tc}/FF_delay.rpt')
ct = ClockTree(raw_tree, lib)
optimize(ct, ss, ff)
results, _, _, _ = ct.compute_slack(ss, ff)
violated = [r for r in results if r['slack_setup'] < 0 or r['slack_hold'] < 0]
sys.stdout = sys.__stdout__
print('PASS' if not violated else 'FAIL')
PYEOF
)
    echo "結果: $result"
    if [ "$result" = "PASS" ]; then
        PASS=$((PASS+1))
    else
        FAIL=$((FAIL+1))
    fi
    echo ""
}

run_test testcase0
run_test testcase1
run_test testcase2
run_test testcase3
run_test testcase_met
run_test testcase_resize

echo "================================"
echo "PASS: $PASS  FAIL: $FAIL"
run_test testcase_hold_resize
