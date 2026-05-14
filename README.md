# 车辆速度跟踪与测速系统

本项目基于 Python 3.9、FastAPI、OpenCV 和 YOLOv8 实现车辆检测、车辆跟踪、轨迹绘制和双线测速功能。

## 功能

- 网页端上传视频
- YOLOv8 检测车辆
- IOU Tracker 跟踪车辆
- 显示车辆方框、车辆 ID
- 显示车辆轨迹
- 支持两条测速线
- 支持网页端调整测速线位置
- 支持设置两条线实际距离
- 使用视频帧号和 FPS 计算速度，不受电脑运行速度影响

## 启动方式

安装依赖：

```bash
pip install -r requirements.txt
````

启动项目：

```bash
python run.py
```

浏览器打开：

```text
http://127.0.0.1:8000
```

## 模型文件

请将 YOLOv8 权重文件放到：

```text
weights/yolov8m.pt
```

## 测速公式

车辆通过两条测速线时，系统记录车辆通过第一条线和第二条线的帧号。

```text
time = frame_diff / fps
speed_mps = distance_m / time
speed_kmh = speed_mps * 3.6
```

本系统不使用程序运行时间计算速度，因此电脑性能不会影响测速结果。





# 运行命令

在项目根目录执行：

```cmd
pip install -r requirements.txt
````

然后：

```cmd
python run.py
```

浏览器打开：

```text
http://127.0.0.1:8000
```

如果 `ultralytics` 或 `torch` 安装比较慢，属于正常情况。第一版跑通后，再继续加：**保存检测结果、导出 Excel、MySQL 入库、检测后生成输出视频**。
