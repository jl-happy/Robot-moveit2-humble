# 协作机械臂上位机（robot_upper_computer）功能与后端接口说明

## 1. 文档目的
本说明用于让后端快速了解：
- 当前上位机已经具备的功能
- 上位机需要后端提供的接口能力
- 推荐的接口数据结构（便于前后端对齐）

> 当前项目已具备可运行 UI 与模拟器流程，后续可将模拟器替换为真实后端通信层。

---

## 2. 当前上位机已具备功能（前端侧）

### 2.1 页面与导航
- 工具栏导航（运行 / 点动 / 监控 / 编程 / 轨迹 / 配置）
- 当前页面状态显示（状态栏）
- 页面切换高亮

### 2.2 运行页
- 显示机器人状态（连接、使能、模式、急停、故障）
- 显示当前程序名
- 显示配置摘要（TCP、工件坐标系）
- 快捷跳转到编程/点动/监控

### 2.3 点动页
- 6 关节点动（正向/反向/停止）
- 急停/急停复位
- 关节位置显示与刷新

### 2.4 编程页
- 程序步骤编辑（MoveJ / MoveL / Wait）
- 添加、删除、上移、下移步骤
- 程序保存/打开（JSON）
- 程序执行控制（运行/停止/暂停/恢复/单步）
- 当前执行行高亮
- 运行前静态校验（基础参数合法性）与错误行定位

### 2.5 轨迹页
- 轨迹录制（采样关节位置）
- 轨迹保存/加载（JSON）
- 轨迹回放（支持倍率）
- 回放前基础校验（急停/故障状态拦截、基础数据有效性检查）

### 2.6 配置页
- TCP 工具坐标系配置入口
- 工件坐标系配置入口
- 安全参数配置入口
- 配置修改后可联动刷新运行页摘要

### 2.7 监控与日志
- 实时监控面板（关节状态等）
- 系统日志列表（INFO/WARN/ERROR）
- 告警历史（WARN/ERROR）
- 日志导出（JSON）

### 2.8 状态持久化
- 运行态保存/恢复（当前页、模式、最近程序名）
- 程序文件保存/加载
- 配置文件 YAML 管理

---

## 3. 后端接口需求总览

建议后端按以下能力提供接口：

1. **连接与会话**：连接状态、心跳、版本信息
2. **机器人状态流**：关节状态 + 机器人状态（高频推送）
3. **运动控制**：点动、停止、使能、模式切换、急停
4. **程序执行**：启动、停止、暂停、恢复、单步、执行进度
5. **轨迹执行**：轨迹上传、校验、执行、停止、进度
6. **配置管理**：TCP/工件/安全参数读取与写入
7. **故障与日志**：故障上报、清故障、事件日志

---

## 4. 推荐接口定义（JSON 语义）

> 可通过 HTTP + WebSocket、或纯 TCP/IPC 实现。以下为语义定义，非强制协议。

### 4.1 连接与系统信息

#### `GET /api/system/info`
返回系统信息：

```json
{
  "name": "robot_backend",
  "version": "1.0.0",
  "robot_model": "UR5e",
  "joint_count": 6,
  "sim_mode": false
}
```

#### `GET /api/system/health`
```json
{
  "connected": true,
  "latency_ms": 8,
  "last_heartbeat": "2026-02-27T10:00:00Z"
}
```

---

### 4.2 实时状态推送（建议 WebSocket）

#### Topic: `robot/state`
推送频率建议：20~50Hz

```json
{
  "timestamp": "2026-02-27T10:00:00.123Z",
  "joint_states": [
    {"id": 0, "name": "joint1", "position": 0.1, "velocity": 0.0, "torque": 1.2, "temperature": 35.0, "is_enabled": true}
  ],
  "robot_status": {
    "is_connected": true,
    "is_enabled": true,
    "is_emergency_stopped": false,
    "is_manual_mode": true,
    "mode": "IDLE",
    "error_code": 0,
    "error_message": "",
    "program_running": false,
    "program_line": 0
  }
}
```

---

### 4.3 运动与控制接口

#### `POST /api/robot/enable`
#### `POST /api/robot/disable`
#### `POST /api/robot/emergency_stop`
#### `POST /api/robot/reset_emergency_stop`
#### `POST /api/robot/clear_error`

通用响应：
```json
{"ok": true, "message": "..."}
```

#### `POST /api/robot/mode`
```json
{"manual": true}
```

#### `POST /api/robot/jog`
```json
{"joint_id": 0, "velocity": 0.5}
```

#### `POST /api/robot/stop_joint`
```json
{"joint_id": 0}
```

---

### 4.4 程序执行接口

#### `POST /api/program/start`
```json
{
  "name": "demo_program",
  "steps": [
    {"id": 1, "line_number": 1, "command": "MoveJ", "parameters": {"target": "0,0,0,0,0,0", "velocity": "0.5"}, "comment": ""},
    {"id": 2, "line_number": 2, "command": "Wait", "parameters": {"time": "1.0"}, "comment": ""}
  ]
}
```

#### `POST /api/program/stop`
#### `POST /api/program/pause`
#### `POST /api/program/resume`
#### `POST /api/program/step`

#### Topic: `program/progress`
```json
{
  "running": true,
  "line": 3,
  "total": 10,
  "state": "RUNNING"
}
```

---

### 4.5 轨迹接口

#### `POST /api/trajectory/validate`
```json
{
  "joint_count": 6,
  "points": [
    {"t": 0.0, "positions": [0,0,0,0,0,0]},
    {"t": 0.05, "positions": [0.01,0,0,0,0,0]}
  ]
}
```

返回：
```json
{"ok": true, "message": "valid"}
```

#### `POST /api/trajectory/start`
```json
{
  "speed_scale": 1.0,
  "points": [
    {"t": 0.0, "positions": [0,0,0,0,0,0]}
  ]
}
```

#### `POST /api/trajectory/stop`

#### Topic: `trajectory/progress`
```json
{"running": true, "index": 12, "total": 300}
```

---

### 4.6 配置接口

#### `GET /api/config/tcp`
#### `PUT /api/config/tcp`

TCP 数据建议：
```json
{
  "tools": [
    {
      "name": "default_gripper",
      "position": [0.0, 0.0, 0.1],
      "orientation_euler": [0.0, 0.0, 0.0],
      "frame_id": "tool0"
    }
  ]
}
```

#### `GET /api/config/work_object`
#### `PUT /api/config/work_object`

#### `GET /api/config/safety`
#### `PUT /api/config/safety`

---

### 4.7 故障/日志接口

#### Topic: `system/alarm`
```json
{
  "time": "2026-02-27T10:00:00Z",
  "level": "ERROR",
  "code": 1001,
  "message": "Joint 2 over limit"
}
```

#### Topic: `system/log`
```json
{
  "time": "2026-02-27T10:00:00Z",
  "level": "INFO",
  "message": "Program started"
}
```

---

## 5. 前后端联调优先级（建议）

### P0（先打通）
1. `robot/state` 实时推送
2. 点动/停止/使能/急停/模式切换
3. 程序 start/stop/pause/resume/step
4. 故障上报与清故障

### P1（提高可用性）
1. 轨迹 validate/start/stop
2. 配置读写接口（TCP/工件/安全）
3. 日志与告警推送

### P2（产品化增强）
1. 稳定性与重连策略
2. 执行结果回执与错误码体系标准化
3. 版本协商与兼容策略

---

## 6. 错误码建议

建议统一错误码区间，便于 UI 处理：
- `1xxx` 通信错误
- `2xxx` 运动控制错误
- `3xxx` 程序执行错误
- `4xxx` 轨迹错误
- `5xxx` 配置错误

返回建议统一结构：

```json
{
  "ok": false,
  "error_code": 4002,
  "error_message": "Trajectory point dimension mismatch"
}
```

---

## 7. 备注
- 当前上位机已具备完整 UI 流程，可直接进入联调阶段。
- 权限与安全流程（账号、角色、审计）本轮未纳入。
- 若后端确认通信方式（HTTP/WS/gRPC/TCP），可再输出一版**可直接对接的 OpenAPI/协议文档**。
