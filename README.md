# SkewFixer

### ICCAD 2026 CAD Contest - Problem D: Timing Fixing by Useful Skew
### 出題單位：瑞昱半導體 Realtek Semiconductor Corp.

## 問題定義

透過 Useful Skew 技術，在 clock tree 中插入 buffer 或調整 buffer 尺寸，以最小面積開銷修復 timing violation。

評分指標：
- SS corner：setup time check（TNS / WNS）
- FF corner：hold time check（TNS / WNS）
- 面積：新增元件的總面積

## 系統架構

parser.py → optimizer.py → writer.py

## 優化策略

Setup violation：先嘗試 resize，不行再插入最小面積 buffer
Hold violation：在 launch FF 上方插入 buffer

## 快速開始

git clone https://github.com/Pric0123/ICCAD---Skew-Fixer.git
cd ICCAD---Skew-Fixer
python3 main.py testcase0 testcase0/modified_clk_tree.structure

## 測試結果

SS TNS: -0.0240 → 0.0000
SS WNS: -0.0120 → +0.0390
FF TNS: 0.0000 → 0.0000
新增面積: 0.2500

## 關於作者

楊元蓁 (Price Yang) | 中原大學 工業與系統工程學系 & 建築學系
willyang2002@gmail.com
