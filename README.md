# 舰瞰：DOTA-v1.0 船舶有向检测与错误归因平台

本项目是一个面向遥感船舶旋转目标检测实验的浏览器 Web 应用。系统使用
YOLOv8n-OBB 检测 DOTA-v1.0 Ship 子集中的船舶，显示旋转框、角度、置信度和
OBB mAP，并通过 Eigen-CAM 与人工记录完成 TP、FP、FN 错误归因。

实验报告所需的指标、曲线、截图与案例位置见 `EXPERIMENT_EVIDENCE.md`。

- 前端：Vue 3、TypeScript、Vite、Element Plus、ECharts
- 后端：FastAPI、Ultralytics、PyTorch
- 训练：推荐使用 Google Colab GPU
- 本地运行：Windows 浏览器应用，默认使用 CPU 推理，不需要 NVIDIA 显卡
- 默认地址：前端 <http://127.0.0.1:5190>，后端 <http://127.0.0.1:8000>

## 1. 项目能做什么

1. 上传单张遥感图像，使用训练好的 `best.pt` 执行船舶旋转框检测。
2. 在检测画布上查看并选择旋转框，读取中心、宽高、角度和置信度。
3. 对 DOTA Ship 训练集或验证集执行批量评估。
4. 计算 Precision、Recall、TP、FP、FN 和官方 OBB mAP。
5. 将预测框与 Ground Truth 按旋转 IoU 一对一匹配并生成对比图。
6. 筛选 TP、FP、FN、混合样本，生成 Eigen-CAM 关注区域。
7. 保存人工错误原因、分析结论和改进方案。
8. 导出单图检测 JSON 与完整评估报告 JSON。

颜色约定：绿色表示已匹配 GT，蓝色表示正确预测，红色表示 FP，黄色表示 FN。

## 2. 目录说明

```text
OrientedDetection_CAM/
├─ backend/                 FastAPI 接口、模型、评估、CAM 和 JSON 存储
├─ frontend/                Vue 3 前端
├─ dataset_tools/           DOTA Ship 子集生成逻辑
├─ detection/               命令行推理、评估和训练入口
├─ scripts/                 下载、数据准备、配置和启动脚本
├─ notebooks/               Google Colab 训练 Notebook
├─ configs/                 数据集配置示例
├─ datasets/dota_ship/      Ship 子集；GitHub 仅保留配置、清单与预览
├─ weights/best.pt          当前使用的模型权重
├─ artifacts/               本地运行结果；GitHub 仅保留精选实验证据
├─ runs/                    Ultralytics 输出；GitHub 仅保留训练曲线与样例
├─ tests/                   后端、几何和数据测试
├─ .env.example             后端配置模板
└─ README.md
```

`artifacts/` 是运行时数据目录。删除其中内容会同时删除网页中的历史评估任务、
样本、检测记录和 CAM 图片。

## 3. 本地目录与 GitHub 源码包

### 3.1 当前本地目录

当前项目已经包含以下关键文件：

```text
weights/best.pt
datasets/dota_ship/dota_ship.yaml
datasets/dota_ship/images/train
datasets/dota_ship/images/val
datasets/dota_ship/labels/train
datasets/dota_ship/labels/val
```

因此，如果只需要运行网页和完成实验，不需要重新下载 DOTA，也不需要重新训练模型。
只需安装本地依赖、检查数据路径并启动前后端。

`.venv/`、`frontend/node_modules/`、完整数据集、完整评估历史和训练输出会继续保存在
当前电脑中，整理 Git 仓库不会影响它们。因此当前目录仍可按第 6 节直接启动。

### 3.2 GitHub 克隆或下载的源码包

GitHub 仓库用于提交和部署展示，包含完整前后端源码、最终 `weights/best.pt`、数据集
配置与预览、Colab Notebook、训练曲线、实验截图和测试代码。为避免仓库体积过大，
以下可重新生成或体积较大的内容不会上传：

- Python 虚拟环境和 `frontend/node_modules/`。
- DOTA Ship 的完整训练/验证图像与标签。
- `datasets/dota_ship-subset.zip`。
- 网页产生的完整上传、推理和评估历史。
- `runs/` 中重复权重和批量训练图片。

从 GitHub 获取项目后，先按第 4 节安装依赖。单图检测可以直接使用仓库中的
`weights/best.pt`；若要执行完整验证集评估，必须再按第 11 节准备 DOTA Ship 数据，
并执行 `configure_dota_ship.py` 更新 YAML 路径。

需要压缩包时，不必另行维护一份容易过期的 ZIP：在 GitHub 仓库页面点击
`Code -> Download ZIP` 即可下载与当前提交完全一致的源码包。

### 3.3 离线数据集

GitHub 源码包不包含完整 DOTA Ship 图像。若在无网络条件下复现，应下载以下两个压缩包：

```text
OrientedDetection_CAM-main.zip       GitHub 下载的源码包
dota_ship-subset.zip                 本项目使用的完整实验子集
```

当前数据包位于 `datasets/dota_ship-subset.zip`，大小约 716 MB，内容已经核验：

| 内容 | 数量 |
| --- | ---: |
| 训练图像 / 标签 | 2336 / 2336 |
| 验证图像 / 标签 | 600 / 600 |
| 数据配置与构建清单 | `dota_ship.yaml`、`manifest.json` |

数据包 SHA-256：

```text
9160E1C6B5D1F8EA09EDC39BF2F614B7F44F38849FB6DC1B06212A8E3DDE2AC6
```

将数据 ZIP 放到源码根目录的 `datasets/` 后执行：

```powershell
Expand-Archive datasets\dota_ship-subset.zip `
  -DestinationPath datasets\dota_ship `
  -Force
python scripts/configure_dota_ship.py datasets/dota_ship
```

## 4. 环境要求

- Windows 10/11
- Python 3.10 至 3.12，推荐 3.12
- Node.js 20 或更高版本
- 至少 8 GB 内存，执行完整验证集 CPU 评估时建议 16 GB
- 建议保留数 GB 空闲空间用于 PyTorch、评估图片和 JSON 结果
- Chrome、Edge 或其他现代浏览器

所有 PowerShell 命令均在项目根目录执行：

```powershell
Set-Location D:\VSCodeprojects\AICS\OrientedDetection_CAM
```

### 4.1 安装 Python 环境

首次使用时创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

如果 PowerShell 阻止激活脚本，可只对当前终端临时放开限制：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

安装后端基础依赖和机器学习依赖：

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-ml.txt
```

`requirements-ml.txt` 包含 PyTorch、Ultralytics、OpenCV 和 Shapely。即使只使用 CPU，
网页的单图检测、验证集评估和 Eigen-CAM 也必须安装这些依赖。

只有在本地重新下载或准备数据集时，才需要安装：

```powershell
python -m pip install -r requirements-data.txt
```

### 4.2 安装前端依赖

```powershell
Set-Location frontend
npm.cmd install
Set-Location ..
```

## 5. 配置后端

后端可以在没有 `.env` 的情况下使用默认配置。为了明确记录当前实验设置，建议首次
运行时从模板创建 `.env`：

```powershell
Copy-Item .env.example .env
```

默认内容：

```dotenv
APP_HOST=127.0.0.1
APP_PORT=8000
MODEL_PATH=weights/best.pt
MODEL_DEVICE=cpu
MODEL_IMAGE_SIZE=640
MODEL_CONFIDENCE=0.25
MODEL_IOU=0.45
ARTIFACTS_DIR=artifacts
DATASET_CONFIG=datasets/dota_ship/dota_ship.yaml
FRONTEND_ORIGIN=http://localhost:5190
```

| 配置项 | 作用 | 建议值 |
| --- | --- | --- |
| `APP_HOST` | 应用主机配置值；启动脚本当前仍固定为 `127.0.0.1` | `127.0.0.1` |
| `APP_PORT` | 应用端口配置值；启动脚本和 Vite 代理当前仍固定为 `8000` | `8000` |
| `MODEL_PATH` | YOLOv8 OBB 权重路径 | `weights/best.pt` |
| `MODEL_DEVICE` | 推理设备 | 无显卡时必须为 `cpu` |
| `MODEL_IMAGE_SIZE` | 默认推理尺寸，也是网页官方 mAP 验证使用的尺寸 | `640` |
| `MODEL_CONFIDENCE` | 后端默认置信度 | `0.25` |
| `MODEL_IOU` | 后端默认 NMS IoU | `0.45` |
| `DATASET_CONFIG` | DOTA Ship YAML 路径 | `datasets/dota_ship/dota_ship.yaml` |
| `ARTIFACTS_DIR` | 上传、评估、CAM 和报告目录 | `artifacts` |
| `FRONTEND_ORIGIN` | 允许访问 API 的前端来源 | `http://localhost:5190` |

修改 `.env` 后必须重启后端才能生效。

### 5.1 检查数据 YAML

`datasets/dota_ship/dota_ship.yaml` 应类似：

```yaml
path: D:/VSCodeprojects/AICS/OrientedDetection_CAM/datasets/dota_ship
train: images/train
val: images/val
test: images/val

names:
  0: ship
```

项目移动到其他目录后，运行以下命令自动重写 `path`：

```powershell
python scripts/configure_dota_ship.py datasets/dota_ship
```

建议使用正斜杠形式的 Windows 绝对路径。`test` 当前指向 `val`，原因是 DOTA 官方
test 集不公开 Ground Truth，本实验使用验证集计算指标。

## 6. 启动、检查与停止

前后端需要在两个独立 PowerShell 终端中运行。

### 6.1 启动后端

在终端 1 中：

```powershell
Set-Location D:\VSCodeprojects\AICS\OrientedDetection_CAM
.\.venv\Scripts\Activate.ps1
.\scripts\start_backend.ps1
```

看到类似下面的输出说明后端已启动：

```text
Uvicorn running on http://127.0.0.1:8000
```

检查地址：

- 健康检查：<http://127.0.0.1:8000/api/health>
- 系统状态：<http://127.0.0.1:8000/api/system>
- Swagger API 文档：<http://127.0.0.1:8000/docs>

### 6.2 启动前端

在终端 2 中：

```powershell
Set-Location D:\VSCodeprojects\AICS\OrientedDetection_CAM
.\scripts\start_frontend.ps1
```

浏览器打开：

```text
http://127.0.0.1:5190
```

Vite 会把 `/api` 和 `/artifacts` 请求代理到 `http://127.0.0.1:8000`。因此进行检测、
评估或查看结果图片时，前后端都必须运行。只启动前端时可以查看界面，但页面会显示
“API 离线”，功能请求无法完成。

### 6.3 正确停止服务

在运行对应服务的终端中按 `Ctrl+C`：

- 后端终端按一次 `Ctrl+C`，停止 Uvicorn 和当前评估任务。
- 前端终端按一次 `Ctrl+C`，停止 Vite。

关闭终端前应先停止服务。不要在评估执行中重启后端，否则该任务可能保留为“执行中”
但不会继续计算。

如果端口被其他遗留进程占用，可先查询进程号：

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
Get-NetTCPConnection -LocalPort 5190 -State Listen
```

确认是本项目进程后再停止：

```powershell
Stop-Process -Id <OwningProcess>
```

### 6.4 修改端口

`scripts/start_backend.ps1` 当前固定使用 `127.0.0.1:8000`，Vite 代理也固定指向 8000。
如果确实需要修改后端端口，必须同时调整启动命令与
`frontend/vite.config.ts` 中的代理地址。例如使用 8010：

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010 --reload
```

然后把 Vite 的两个代理目标改为 `http://127.0.0.1:8010` 并重启前端。

## 7. 网页操作说明

### 7.1 实验总览

进入网页后的默认页面是“实验总览”。建议每次实验先检查这里。

1. 查看左下角“模型状态”。显示“已就绪”表示机器学习依赖和权重均可用。
2. 查看“运行条件”中的后端 API、模型权重和 DOTA Ship 数据。
3. 查看最新评估的 `mAP@0.5`、`mAP@0.5:0.95`、FP 和 FN。
4. “样本构成”显示 TP、FP、FN、混合样本数量。
5. “错误归因排行”统计在错误归因页面保存过的人工原因标签。
6. 修改数据、权重或完成评估后，点击右上角“刷新”。

状态含义：

- `可用`：路径存在或服务可以访问。
- `待配置`：权重不存在，或尚未安装 `requirements-ml.txt`。
- `API 离线`：后端未启动、后端启动失败或端口不一致。

### 7.2 单图检测

“单图检测”用于快速验证模型是否能在一张遥感图像中找到船舶。

1. 点击或拖拽图像到“选择遥感图像”区域。
2. 推荐优先使用 JPG 或 PNG。后端也接受 BMP、TIF 和 TIFF，但部分浏览器不能直接
   预览 TIFF。
3. 设置“置信度阈值”。默认 `0.25`：
   - 降低到 `0.10` 至 `0.20` 可以找回更多小船，但 FP 通常会增加。
   - 提高到 `0.40` 至 `0.60` 可以减少误检，但可能漏掉小目标。
4. 设置“NMS IoU”。默认 `0.45`：
   - 较低值更积极地删除重叠预测框。
   - 较高值会保留更多相邻或重叠预测框。
5. 选择输入尺寸：
   - `512`：CPU 更快，适合快速预览。
   - `640`：推荐默认值，速度和精度较平衡。
   - `800`：可能改善小目标，但 CPU 推理明显更慢。
6. 点击“执行检测”，等待按钮结束加载状态。
7. 在检测画布点击任意旋转框，右侧会显示目标中心、宽度、高度、角度和置信度。
8. 使用画布右上角开关显示或隐藏标签。
9. 点击页面右上角“导出 JSON”，保存当前检测的完整结果。

检测结果会同时保存在：

```text
artifacts/uploads/                 上传的原始图像
artifacts/inferences/<id>.json     检测结果
```

第一次检测通常较慢，因为后端需要首次加载 PyTorch 模型。后续检测会复用已加载模型。

### 7.3 验证集评估

“验证集评估”会逐张执行 CPU 推理、旋转 IoU 匹配并调用 Ultralytics 计算官方 OBB
mAP。完整验证集在 CPU 上可能需要较长时间，执行期间不要关闭后端。

1. “数据配置”填写 YAML 路径。默认使用
   `datasets/dota_ship/dota_ship.yaml`，也可以填写绝对路径。
2. “数据拆分”通常选择“验证集”。训练集适合排查过拟合，不用于最终实验结论。
3. “置信度阈值”控制用于 TP/FP/FN 人工匹配分析的预测框，建议 `0.25`。
4. “匹配 IoU”决定预测框与 GT 是否匹配，默认 `0.50`。
5. “输入尺寸”控制逐图匹配阶段的推理尺寸，推荐 `640`。
6. 点击“开始评估”。同一时间网页只允许提交一个活动任务。
7. 在“评估任务”表格查看排队、执行进度、当前阶段和图像数量。
8. 点击表格中的任务行，将其设为当前任务并查看指标和匹配统计。
9. 任务完成后点击“报告”，下载包含指标、样本和人工归因的 JSON。

指标说明：

| 指标 | 含义 |
| --- | --- |
| `Precision` | `TP / (TP + FP)`，预测为船舶的目标中有多少是正确的 |
| `Recall` | `TP / (TP + FN)`，真实船舶中有多少被检出 |
| `mAP@0.5` | 旋转框 IoU 0.5 下的平均精度 |
| `mAP@0.5:0.95` | IoU 0.5 到 0.95 多阈值平均，更严格的综合指标 |
| `TP` | 与 Ground Truth 成功匹配的预测 |
| `FP` | 没有匹配 Ground Truth 的错误预测 |
| `FN` | 没有被预测匹配的真实目标 |

注意：页面的“输入尺寸”用于逐图 TP/FP/FN 匹配；当前实现中官方 OBB mAP 使用
`.env` 的 `MODEL_IMAGE_SIZE`。要统一两者，请将二者都设为 `640`。

每个任务结果保存在：

```text
artifacts/evaluations/<任务ID>/job.json
artifacts/evaluations/<任务ID>/samples.json
artifacts/evaluations/<任务ID>/images/
artifacts/evaluations/<任务ID>/report.json
```

### 7.4 错误样本归因

该页面只有在至少一次评估成功后才会出现样本。

1. 用第一个下拉框选择某次已完成的评估任务。
2. 用分段按钮筛选：
   - `TP`：没有 FP 或 FN 的正确样本。
   - `FP`：存在误检但不存在漏检。
   - `FN`：存在漏检但不存在误检。
   - `混合`：同一张图同时存在 FP 和 FN。
3. 在搜索框输入文件名并按 Enter。
4. 从左侧样本队列选择一张图。
5. 使用“原图 / 检测对比 / Eigen-CAM”切换图像模式。
6. 检测对比图中查看 GT、TP、FP 和 FN 的位置关系。
7. 如果还没有 CAM，点击“生成 Eigen-CAM”。CPU 生成需要等待一段时间。
8. 根据图像填写：
   - 模型是否关注目标区域。
   - 是否受到背景区域干扰。
   - 是否遗漏关键特征。
   - 小目标、密集目标、纹理干扰、角度偏差等可能原因。
   - 分析结论和改进方案。
9. 点击“保存分析”。保存后总览页的“错误归因排行”会更新。

CAM 图片保存在：

```text
artifacts/cams/<样本ID>.jpg
```

人工归因写回对应任务的 `samples.json`。生成 CAM 或保存结论后，不要手动删除该评估
任务目录，否则网页将无法恢复记录。

## 8. 配置建议

### 8.1 推荐的 CPU 实验配置

```text
设备：cpu
输入尺寸：640
单图置信度：0.25
NMS IoU：0.45
评估匹配 IoU：0.50
评估拆分：val
```

先用一张 JPG/PNG 完成单图检测，确认模型可以工作，再启动完整验证集评估。若只想
演示网页流程，可准备一个小型 YAML，将 `val` 指向少量图像的目录，以缩短 CPU 评估
时间。

### 8.2 更换模型权重

1. 将新的 Ultralytics OBB 权重放入 `weights/`。
2. 修改 `.env` 的 `MODEL_PATH`。
3. 确保新模型的类别 `0` 仍为 `ship`。
4. 重启后端。
5. 在实验总览确认模型状态为“已就绪”。
6. 先执行单图检测，再执行验证集评估。

只替换文件但不重启后端时，已经加载到内存中的旧模型可能继续被使用。

### 8.3 更换数据集位置

数据集必须保持 YOLO OBB 目录结构：

```text
dataset_root/
├─ images/train/
├─ images/val/
├─ labels/train/
├─ labels/val/
└─ dataset.yaml
```

每行标签必须是 YOLO OBB 四点格式：

```text
class_id x1 y1 x2 y2 x3 y3 x4 y4
```

八个坐标均为相对于图像宽高归一化后的数值。修改位置后更新 YAML 的 `path` 和
`.env` 的 `DATASET_CONFIG`，然后重启后端。

## 9. 常见问题

### 9.1 页面显示“API 离线”

1. 确认后端终端仍在运行。
2. 打开 <http://127.0.0.1:8000/api/health>，应返回 `{"status":"ok"}`。
3. 确认前端是通过 `http://127.0.0.1:5190` 打开的。
4. 检查 8000 端口是否被其他程序占用。

### 9.2 页面显示“未安装机器学习依赖”

确保激活的是项目虚拟环境，然后安装：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-ml.txt
```

安装完成后重启后端。仅安装 `requirements.txt` 只能启动基础 API，不能推理。

### 9.3 页面显示“未找到模型权重”

检查：

```powershell
Test-Path weights\best.pt
```

如果权重放在其他位置，修改 `.env` 中的 `MODEL_PATH` 并重启后端。

### 9.4 数据状态显示“待配置”或评估提示没有图像

```powershell
Test-Path datasets\dota_ship\dota_ship.yaml
python scripts/configure_dota_ship.py datasets/dota_ship
```

然后检查 YAML 指向的 `images/val` 是否存在图像，`labels/val` 是否有同名 `.txt`
标签。

### 9.5 CPU 推理或评估很慢

- 单图检测先选 `512` 或 `640`。
- 完整评估前先用少量验证图像验证流程。
- 关闭其他高 CPU 占用程序。
- 不要同时启动多个评估任务。
- 正式训练仍建议在 Google Colab GPU 上完成。

### 9.6 评估任务长期停留在“执行中”

后端可能在任务执行中被关闭。当前版本会在后端重新启动时，将磁盘中遗留的
`queued/running` 任务自动标记为“失败”，并提示重新创建任务。后台评估线程不能跨
进程恢复，因此原任务无法从已有进度继续。

如果是旧版本留下的任务，检查后端终端和
`artifacts/evaluations/<任务ID>/job.json`。确认任务确实中断后，可以备份并删除对应
任务目录，再重新提交评估。

### 9.7 评估出现 `WinError 5` 或 `job.json.tmp` 拒绝访问

这是 Windows 在页面轮询任务状态、评估线程写入状态或安全软件扫描文件时产生的短暂
文件占用，不是模型或数据集错误。当前版本已让任务读写共用同一存储锁，并在临时文件
替换遇到占用时自动重试。

已因此失败的任务不能继续运行，但不会阻止创建新任务。刷新页面后重新点击“开始评估”
即可。若需要清除失败记录，先停止后端，再删除对应目录：

```powershell
Remove-Item artifacts\evaluations\<任务ID> -Recurse -Force
```

### 9.8 页面能打开但样式或请求异常

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run typecheck
npm.cmd run build
```

开发模式必须通过 Vite 地址访问，不要直接双击 `frontend/index.html`。

## 10. 结果与备份

完成实验后建议备份：

```text
weights/best.pt
datasets/dota_ship/dota_ship.yaml
artifacts/evaluations/
artifacts/cams/
artifacts/colab-evaluation.json
runs/dota_ship/yolov8n-obb-colab/
```

不需要长期保留的临时内容：

- `artifacts/uploads/` 中不再使用的上传图像。
- `artifacts/inferences/` 中不再使用的单图 JSON。
- 可重新生成的前端 `frontend/dist/`。

清理前必须先停止前后端并做好备份，不要删除仍被错误归因页面引用的评估图片。

## 11. 重新获取 DOTA-v1.0 数据

当前项目已有数据时可跳过本节。

安装 ModelScope 依赖：

```powershell
python -m pip install -r requirements-data.txt
```

固定下载到项目目录：

```powershell
python scripts/download_dota_modelscope.py --cache-dir datasets/modelscope-cache
```

脚本通过 ModelScope Hub 下载 `yolo_master/DOTAv1` 中的 `DOTAv1.zip`。随后生成紧凑
Ship 子集：

```powershell
python scripts/prepare_dota_ship.py datasets/modelscope-cache `
  --output datasets/dota_ship `
  --work-dir datasets/dota_work `
  --crop-size 1024 `
  --gap 200 `
  --negative-ratio 0.25 `
  --max-train 2500 `
  --max-val 600
```

准备脚本接受 ModelScope 缓存目录、`DOTAv1.zip` 或已解压数据目录。输出包括：

```text
datasets/dota_ship/
├─ images/train
├─ images/val
├─ labels/train
├─ labels/val
├─ previews
├─ manifest.json
└─ dota_ship.yaml
```

必须人工抽查 `previews/` 中的旋转框。`manifest.json` 记录正负图块数、船舶实例数、
切片参数和输入路径。

## 12. Google Colab 训练

当前项目已有 `weights/best.pt` 时可跳过本节。

1. 将项目上传到 Google Drive，例如 `MyDrive/OrientedDetection_CAM`。
2. 在 Colab 打开 `notebooks/dotav1_ship_yolov8n_obb_colab.ipynb`。
3. 选择“运行时 -> 更改运行时类型 -> GPU”。
4. 修改 Notebook 的 `PROJECT_DIR`。
5. 按顺序运行所有单元格。
6. 默认训练参数为 80 epochs、640 输入尺寸、batch 16；显存不足时将 batch 改为 8。

训练结束后带回本地的主要文件：

```text
weights/best.pt
runs/dota_ship/yolov8n-obb-colab/
artifacts/colab-evaluation.json
datasets/dota_ship-subset.zip
```

解压子集并重写 YAML 路径：

```powershell
Expand-Archive datasets\dota_ship-subset.zip -DestinationPath datasets\dota_ship
python scripts/configure_dota_ship.py datasets\dota_ship
```

如果目标目录已有同名文件，不要直接覆盖。先备份现有 `datasets/dota_ship`，再解压并
检查实际目录层级。

## 13. 命令行使用

不启动网页也可以直接执行推理：

```powershell
.\.venv\Scripts\Activate.ps1
python -m detection.infer path\to\image.jpg `
  --weights weights\best.pt `
  --imgsz 640 `
  --conf 0.25 `
  --device cpu
```

输出默认写入 `runs/inference/latest/`。

命令行评估：

```powershell
python -m detection.evaluate `
  --weights weights\best.pt `
  --data datasets\dota_ship\dota_ship.yaml `
  --split val `
  --imgsz 640 `
  --device cpu `
  --output artifacts\cli-evaluation.json
```

## 14. 测试与前端构建

安装开发依赖并运行 Python 测试：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
```

检查并构建前端：

```powershell
Set-Location frontend
npm.cmd run typecheck
npm.cmd run build
Set-Location ..
```

生产构建输出到 `frontend/dist/`。

## 15. API 速查

| 方法 | 地址 | 用途 |
| --- | --- | --- |
| `GET` | `/api/health` | 后端健康检查 |
| `GET` | `/api/system` | 模型、数据集和设备状态 |
| `POST` | `/api/inference` | 单图 OBB 推理 |
| `GET` | `/api/evaluations` | 评估任务列表 |
| `POST` | `/api/evaluations` | 创建评估任务 |
| `GET` | `/api/evaluations/{id}` | 查询单个评估任务 |
| `GET` | `/api/samples` | 查询 TP、FP、FN 样本 |
| `PUT` | `/api/samples/{id}/analysis` | 保存人工归因 |
| `POST` | `/api/samples/{id}/cam` | 生成 Eigen-CAM |
| `GET` | `/api/statistics` | 总览统计 |
| `GET` | `/api/reports/{id}` | 导出评估 JSON 报告 |

完整请求参数和响应结构以 <http://127.0.0.1:8000/docs> 为准。
