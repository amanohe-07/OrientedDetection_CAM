# 实验材料索引

本文件记录项目清理后保留的关键实验依据。撰写实验报告、制作答辩截图或复现实验时，
优先使用下列文件，不要将它们当作运行垃圾删除。

最终课程设计报告：`遥感船舶有向检测与错误归因平台实验报告.docx`。报告依据学校模板
第 8-16 页格式编排，包含 8 章正文、8 张数据表和 11 幅实验图。

## 1. 数据集依据

- 数据配置：`datasets/dota_ship/dota_ship.yaml`
- 数据清单：`datasets/dota_ship/manifest.json`
- 可迁移子集：`datasets/dota_ship-subset.zip`
- 标注预览：`datasets/dota_ship/previews/`

最终子集参数：

| 项目 | 训练集 | 验证集 |
| --- | ---: | ---: |
| 正样本图块 | 1869 | 480 |
| 困难负样本图块 | 467 | 120 |
| 船舶实例 | 57616 | 14152 |

切片尺寸为 1024，重叠区域为 200，类别为单类别 `ship`。

## 2. 模型与训练过程

- 网页实际加载权重：`weights/best.pt`
- Colab 最优/末轮权重：`runs/dota_ship/yolov8n-obb-colab/weights/`
- 训练参数：`runs/dota_ship/yolov8n-obb-colab/args.yaml`
- 每轮指标：`runs/dota_ship/yolov8n-obb-colab/results.csv`
- 训练总览图：`runs/dota_ship/yolov8n-obb-colab/results.png`
- PR、P、R、F1 曲线：`runs/dota_ship/yolov8n-obb-colab/Box*_curve.png`
- 混淆矩阵：`runs/dota_ship/yolov8n-obb-colab/confusion_matrix*.png`
- 标签统计和训练批次：`runs/dota_ship/yolov8n-obb-colab/labels*`、`train_batch*`
- 验证标签/预测对照：`runs/dota_ship/yolov8n-obb-colab/val_batch*`
- 训练 Notebook：`notebooks/dotav1_ship_yolov8n_obb_colab.ipynb`

## 3. 最终指标

Colab 官方验证结果位于 `artifacts/colab-evaluation.json`：

| 指标 | 数值 |
| --- | ---: |
| mAP@0.5 | 0.922693 |
| mAP@0.5:0.95 | 0.757946 |
| mAP@0.75 | 0.906087 |

本地网页完整评估任务为 `a35984300f72`，配置为 CPU、640 输入尺寸、置信度 0.25、
匹配 IoU 0.50：

| 指标 | 数值 |
| --- | ---: |
| 验证图像 | 600 |
| TP | 12513 |
| FP | 2091 |
| FN | 1639 |
| Precision | 0.8568 |
| Recall | 0.8842 |
| F1 | 0.8703 |
| mAP@0.5 | 0.9227 |
| mAP@0.5:0.95 | 0.7579 |

任务文件：

- `artifacts/evaluations/a35984300f72/job.json`
- `artifacts/evaluations/a35984300f72/samples.json`
- `artifacts/evaluations/a35984300f72/images/`

样本类型分布：TP 189、FP 184、FN 43、混合 184，共 600 张。

## 4. 错误归因与 CAM

- Eigen-CAM 图片：`artifacts/cams/`
- 人工归因字段：保存在成功任务的 `samples.json`
- 原图和检测对照图：保存在成功任务的 `images/`

当前保留 2 张 CAM 图片和 1 条已填写的人工归因，可作为错误分析章节示例。完整
`samples.json` 必须与任务图片目录一起保留，否则网页无法还原错误样本。

## 5. 网页效果截图

最终桌面截图：

- `artifacts/desktop-dashboard.png`
- `artifacts/desktop-detect.png`
- `artifacts/desktop-evaluate.png`
- `artifacts/desktop-analysis.png`

最终移动端截图：

- `artifacts/mobile-dashboard.png`
- `artifacts/mobile-detect.png`
- `artifacts/mobile-evaluate.png`
- `artifacts/mobile-analysis.png`

截图自动检查脚本为 `artifacts/visual-check.mjs`。

## 6. 单图检测示例

- 上传图像：`artifacts/uploads/`
- 推理 JSON：`artifacts/inferences/`

当前仅保留一组单图推理示例，适合用于报告中的功能流程说明。

## 7. 2026-07-14 清理记录

已删除：

- Python `__pycache__` 和 `.pyc`
- `.pytest_cache`、`.ruff_cache`
- 可重新构建的 `frontend/dist`
- 前后端临时日志
- 早期 HRSC 下载探测文件
- 两张被最终按页面截图替代的早期重复截图
- 空的 ModelScope 缓存目录和旧 `datasets/raw` 目录

明确保留：

- `.venv` 和 `frontend/node_modules`，保证无需重装即可继续运行
- 最终数据集、子集压缩包、模型权重
- Colab Notebook、训练/验证曲线和批次对照图
- 成功网页评估、CAM、单图检测示例和最终 UI 截图

清理后已执行后端 12 项测试和前端 TypeScript 类型检查，结果全部通过。
