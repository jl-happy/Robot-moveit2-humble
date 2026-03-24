# 后端联调请求示例（基于 `openapi_backend.yaml`）

> 默认后端地址：`http://127.0.0.1:8000`

## 1. 系统信息与健康检查

### 获取系统信息

```bash
curl -X GET "http://127.0.0.1:8000/api/system/info"
```

### 获取健康状态

```bash
curl -X GET "http://127.0.0.1:8000/api/system/health"
```

---

## 2. 机器人控制

### 机器人使能

```bash
curl -X POST "http://127.0.0.1:8000/api/robot/enable"
```

### 机器人去使能

```bash
curl -X POST "http://127.0.0.1:8000/api/robot/disable"
```

### 急停

```bash
curl -X POST "http://127.0.0.1:8000/api/robot/emergency-stop"
```

### 急停复位

```bash
curl -X POST "http://127.0.0.1:8000/api/robot/reset-emergency-stop"
```

### 清除故障

```bash
curl -X POST "http://127.0.0.1:8000/api/robot/clear-error"
```

### 切换模式（手动/自动）

```bash
curl -X POST "http://127.0.0.1:8000/api/robot/mode" \
  -H "Content-Type: application/json" \
  -d "{\"manual\": false}"
```

### 点动关节

```bash
curl -X POST "http://127.0.0.1:8000/api/robot/jog" \
  -H "Content-Type: application/json" \
  -d "{\"joint_id\": 1, \"velocity\": 0.3}"
```

### 停止单关节

```bash
curl -X POST "http://127.0.0.1:8000/api/robot/stop-joint" \
  -H "Content-Type: application/json" \
  -d "{\"joint_id\": 1}"
```

---

## 3. 程序执行

### 启动程序

```bash
curl -X POST "http://127.0.0.1:8000/api/program/start" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"demo_program\",
    \"steps\": [
      {
        \"id\": 1,
        \"command\": \"MoveJ\",
        \"parameters\": {\"target\": \"0,0,0,0,0,0\", \"velocity\": \"0.5\"},
        \"comment\": \"回零\",
        \"line_number\": 1
      },
      {
        \"id\": 2,
        \"command\": \"Wait\",
        \"parameters\": {\"time\": \"1.0\"},
        \"comment\": \"等待稳定\",
        \"line_number\": 2
      }
    ]
  }"
```

### 暂停程序

```bash
curl -X POST "http://127.0.0.1:8000/api/program/pause"
```

### 恢复程序

```bash
curl -X POST "http://127.0.0.1:8000/api/program/resume"
```

### 单步执行

```bash
curl -X POST "http://127.0.0.1:8000/api/program/step"
```

### 停止程序

```bash
curl -X POST "http://127.0.0.1:8000/api/program/stop"
```

---

## 4. 轨迹接口

### 校验轨迹

```bash
curl -X POST "http://127.0.0.1:8000/api/trajectory/validate" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"traj_pick_01\",
    \"joint_count\": 6,
    \"points\": [
      {\"t\": 0.00, \"positions\": [0,0,0,0,0,0]},
      {\"t\": 0.05, \"positions\": [0.1,0,0,0,0,0]},
      {\"t\": 0.10, \"positions\": [0.2,0,0,0,0,0]}
    ]
  }"
```

### 开始回放轨迹

```bash
curl -X POST "http://127.0.0.1:8000/api/trajectory/start" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"traj_pick_01\",
    \"speed_ratio\": 1.0,
    \"points\": [
      {\"t\": 0.00, \"positions\": [0,0,0,0,0,0]},
      {\"t\": 0.05, \"positions\": [0.1,0,0,0,0,0]}
    ]
  }"
```

### 停止回放轨迹

```bash
curl -X POST "http://127.0.0.1:8000/api/trajectory/stop"
```

---

## 5. 配置接口

### 获取 TCP 配置

```bash
curl -X GET "http://127.0.0.1:8000/api/config/tcp"
```

### 更新 TCP 配置

```bash
curl -X PUT "http://127.0.0.1:8000/api/config/tcp" \
  -H "Content-Type: application/json" \
  -d "{
    \"tools\": [
      {
        \"name\": \"default_gripper\",
        \"position\": [0.0, 0.0, 0.1],
        \"orientation_euler\": [0.0, 0.0, 0.0],
        \"frame_id\": \"tool0\"
      }
    ]
  }"
```

### 获取工件坐标系配置

```bash
curl -X GET "http://127.0.0.1:8000/api/config/work-object"
```

### 更新工件坐标系配置

```bash
curl -X PUT "http://127.0.0.1:8000/api/config/work-object" \
  -H "Content-Type: application/json" \
  -d "{
    \"work_objects\": [
      {
        \"name\": \"base\",
        \"position\": [0.0, 0.0, 0.0],
        \"orientation_euler\": [0.0, 0.0, 0.0],
        \"frame_id\": \"world\",
        \"user_frame_id\": 0
      }
    ]
  }"
```

### 获取安全参数

```bash
curl -X GET "http://127.0.0.1:8000/api/config/safety"
```

### 更新安全参数

```bash
curl -X PUT "http://127.0.0.1:8000/api/config/safety" \
  -H "Content-Type: application/json" \
  -d "{
    \"joint_limits_deg\": [[-360,360],[-180,180],[-180,180],[-360,360],[-360,360],[-360,360]],
    \"tcp_max_velocity\": 1.0,
    \"tcp_max_acceleration\": 3.0,
    \"collision_sensitivity\": 3,
    \"enable_soft_limits\": true,
    \"enable_collision_detection\": true
  }"
```

---

## 6. WebSocket 实时订阅示例

> 建议地址：`ws://127.0.0.1:8000/ws`

### Python 客户端示例

```python
import json
import websocket


def on_open(ws):
    ws.send(json.dumps({"action": "subscribe", "topic": "robot/status"}))
    ws.send(json.dumps({"action": "subscribe", "topic": "robot/joint_states"}))
    ws.send(json.dumps({"action": "subscribe", "topic": "system/logs"}))


def on_message(ws, message):
    print("RECV:", message)


ws = websocket.WebSocketApp(
    "ws://127.0.0.1:8000/ws",
    on_open=on_open,
    on_message=on_message,
)
ws.run_forever()
```

---

## 7. 通用响应约定示例

### 成功

```json
{
  "success": true,
  "message": "ok",
  "error_code": 0
}
```

### 失败

```json
{
  "success": false,
  "message": "当前处于急停状态",
  "error_code": 1001
}
```
