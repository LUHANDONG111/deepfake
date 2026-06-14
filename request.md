# 纯视觉多模态解耦 Deepfake 视频检测系统 — 开发设计文档
(Face Deepfake Video Detection System Based on Layered Pipe-and-Filter Architecture)

## 一、 引言 (Introduction)

### 1.1 文档目的
本规划文档旨在将原有的纯视觉单机检测脚本，重构并升级为基于 **Flask 前后端分离架构** 的现代化 Web 应用程序。本应用的核心算法基于预训练的 RetinaFace（人脸检测与仿射对齐）与微调后的 Xception（二分类伪造判定模型），整体设计严格遵循“管道-过滤器（Pipe-and-Filter）”的流式数据处理理念。

### 1.2 项目背景与核心痛点
在前期的学术研究中，微调后的 Xception 模型在验证集上取得了 96.14% 的分类准确率与 92.80% 的最高 F1 分数，算法本身的有效性已得到验证。然而，在 Apple M2 (8GB) 硬件平台部署时，RetinaFace 与 Xception 串联推理造成了明显的显存与计算瓶颈，无法在全量逐帧检测下达到 10 FPS 的实时吞吐量目标。
为了解决高延迟任务阻塞 Web 线程导致网页超时崩溃的问题，并有效落地论文中提出的“动态跳帧策略”与“滑动窗口平滑算法”，本系统特采用非阻塞的“多线程任务隔离驱动”方案。

---

## 二、 系统架构设计 (Architectural Design)

本系统采用经典的 **四层分层架构（Layered Architecture）**，各层之间通过标准定义边界进行通信，确保前后端完全解耦。

### 2.1 用户界面显示层 (Presentation Layer)
* **实现形式：** 单页应用（SPA）思想，基于 HTML5 + Tailwind CSS + Vanilla JavaScript 构建。
* **交互逻辑：** 1.  **任务配置状态（Setup View）：** 提供文件拖拽上传组件，开放决策阈值 $T$、时序滑窗大小 $N$ 以及动态跳帧率（Skip Rate）的参数调节滑块。
    2.  **流式处理状态（Processing View）：** 阻断用户重复提交，通过高频轮询异步接口，动态渲染亮蓝色的进度条（0% -> 100%）。
    3.  **分析总结状态（Summary View）：** 呈现最终的学术审计结论（FAKE / REAL 看板），并提供规范化 CSV 报告的下载链接。

### 2.2 应用控制与网关层 (Application / Controller Layer)
* **实现形式：** 基于 Flask 轻量级 Web 框架，仅作为 RESTful API 请求调度网关。
* **核心职责：** 接收多媒体文件，生成全局唯一的 Session ID（UUID），在数据库中初始化任务会话。随后克隆并分发独立后台工作线程（Background Thread）接管重负载计算，立即向前端返回任务凭证，避免同步阻塞。

### 2.3 视觉推理引擎层 (Inference Engine Layer)
* **实现形式：** 纯 Python 工艺，封装 PyTorch、Torchaudio 与 OpenCV。
* **流水线（Filter）流转顺序：**
    `视频流读取` ──> `动态跳帧过滤器` ──> `RetinaFace 人脸追踪` ──> `人脸 5 点仿射校正对齐` ──> `Xception 假脸分类器` ──> `Sliding Window 时序平滑器` ──> `会话判决器`

### 2.4 基础设施与数据持久层 (Infrastructure & Data Layer)
* **实现形式：** SQLite 嵌入式数据库 + Flask-SQLAlchemy 对象关系映射器。
* **核心职责：** 负责检测会话（Session）状态的生命周期维护、系统 Runtime 崩溃日志捕获，以及将帧级和视频级推断元数据导出为 CSV/JSON 审计报告。

---

## 三、 数据库模式与数据字典 (Database Scheme)

系统底层依赖极为轻量的数据方案，完美映射学术设计类图。

### 3.1 TaskSession 实体表（检测任务会话）
* `id` (String, 36位 UUID, 主键): 全局唯一的检测任务标识。
* `video_path` (String, 255位): 用户上传的原始 `.mp4` 文件在服务器磁盘上的存储相对路径。
* `status` (String, 20位): 任务当前的生命周期状态，限定为：`PENDING`（排队等待）、`PROCESSING`（处理中）、`SUCCESS`（分析成功完成）、`FAILED`（异常失败）。
* `progress` (Integer): 处理进度百分比，取值范围 0 至 100。
* `final_score` (Float): Xception 经时序平滑后计算出的全局伪造平均概率（0.0 ~ 1.0）。
* `final_verdict` (String, 10位): 系统的最终学术判决结论：`REAL`（真）或 `FAKE`（假）。
* `created_at` (DateTime): 任务创建的服务器绝对时间戳。

---

## 四、 核心过滤器（Filters）逻辑规范

### 4.1 动态跳帧过滤器 (Dynamic Frame-Skipping)
* **输入：** 原始视频帧序列，前端配置的跳帧率 `skip_rate`（默认 2）。
* **逻辑：** 针对帧索引执行模运算（`frame_idx % skip_rate != 0`）。若满足条件则直接丢弃该帧，不加载进内存，规避 M2 硬件由于逐帧解码和全量模型调度带来的 I/O 与算力过载。

### 4.2 人脸 5 点仿射变换对齐过滤器 (RetinaFace Alignment)
* **输入：** 被抽检的有效视频帧（RGB 矩阵）。
* **逻辑：** 1.  运行预训练的 RetinaFace 定位面部边界框，提取左眼、右眼、鼻子、左嘴角、右嘴角 5 个空间特征点。
    2.  计算左眼与右眼中心坐标之间的倾斜垂直高度差 $\Delta Y$ 与水平跨度差 $\Delta X$。
    3.  通过反正切函数计算面部倾斜角度：$\theta = \text{atan2}(\Delta Y, \Delta X)$。
    4.  以双眼中心为原点，构建二维旋转矩阵，利用仿射变换（Affine Transformation）将面部姿态旋转至水平基准线。
    5.  将变换后的区域标准化裁剪为归一化图像块，消除背景噪声和头部姿态对后续检测的干扰。

### 4.3 Xception 伪造分类分类器 (Xception Classifier)
* **输入：** 标准化裁剪后的面部图像。
* **逻辑：** 1.  将像素值从 0–255 缩放到 0–1 范围，图像尺寸调整为标准 `(299, 299)`。
    2.  应用均值和标准差为 `[0.5, 0.5, 0.5]` 的归一化张量转换。
    3.  关闭梯度计算（`torch.no_grad()`），执行前向传播。
    4.  通过 Softmax 激活函数将 Logit 转换为假脸概率分数。

### 4.4 滑动窗口时序平滑过滤器 (Sliding-Window Smoother)
* **输入：** 当前帧模型输出的原始概率分数，前端配置的滑窗最大长度 $N$（默认 5）。
* **逻辑：** 系统维护一个先进先出（FIFO）的双端队列。每当检测到有效新分数，将其推入队列。计算队列内所有历史分数的算术平均值作为该帧的平滑得分。
* **目的：** 利用时间序列连续性约束，有效过滤掉由于突然的照明变化、运动模糊或噪点引发的单帧预测标签“发生跳变与闪烁”的问题。

---

## 五、 RESTful API 通信契约设计 (API Contracts)

前后端解耦交互严格基于以下三个接口：

### 5.1 提交检测任务 (Upload Stream)
* **端点：** `POST /api/upload`
* **请求类型：** `multipart/form-data`
* **请求Payload：**
    * `file`: 视频二进制流文件 (Required)。
    * `threshold`: 判定阈值，默认 0.5 (Optional)。
    * `window_size`: 滑窗大小，默认 5 (Optional)。
    * `skip_rate`: 跳帧采样率，默认 2 (Optional)。
* **后端响应（立即返回，不等待推理）：**
    ```json
    {
      "status": "success",
      "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
    }
    ```

### 5.2 状态进度轮询 (Status Polling)
* **端点：** `GET /api/status/<task_id>`
* **后端响应（进行中）：**
    ```json
    {
      "status": "PROCESSING",
      "progress": 45
    }
    ```

### 5.3 获取学术审计报告 (Result Fetching)
* **端点：** `GET /api/result/<task_id>`
* **前端触发条件：** 当轮询检测到状态变为 `SUCCESS` 时触发。
* **后端响应（成功）：**
    ```json
    {
      "task_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "status": "SUCCESS",
      "final_verdict": "FAKE",
      "final_score": 0.7842,
      "video_url": "/static/uploads/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d.mp4",
      "report_url": "/static/reports/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d.csv"
    }
    ```

---

## 六、 系统错误处理与鲁棒性策略 (Exception Handling)

为满足论文 D7 章节对系统高稳定性的设计规范，后端必须实现以下容错兜底机制：
1.  **无脸帧健壮跳过：** 在处理循环中，若 RetinaFace 返回的检测列表为空（即当前帧无目标或受极限光照/遮挡干扰），系统应立即捕获该状态，在数据库写入一条 `INFO` 日志，放弃 Xception 推理，直接跳过并读取下一帧，防止空指针异常或张量不匹配导致服务挂起。
2.  **受损/不支持文件拦截：** 若 OpenCV 在初始化 `cv2.VideoCapture` 时无法读取视频头，或视频总帧数为 0，系统应立即更改当前 `TaskSession` 状态为 `FAILED` 并持久化入库，向客户端轮询返回错误信号，随后平稳释放视频硬件句柄，终止线程。
3.  **多目标独立评估：** 若视频帧内存在多张面部，系统需在 Filter 内部展开二级循环，对每一张人脸独立执行仿射对齐和 Xception 分类，最终取该帧内最高的一分作为该帧的风险评估，实现宁可错杀、绝不放过的安全审计准则。