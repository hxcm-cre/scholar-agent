本目录用于存放本地实验数据（CSV），例如 EKF 姿态估计误差曲线或估计/真值序列。

建议列名（任选其一即可）：

1) 直接给误差列：
- `error` 或 `err`（单位可为 deg 或 rad，建议在文件名/README 中标注）

2) 给估计与真值（支持 roll/pitch/yaw 或任意维度）：
- `roll_est`, `roll_gt`, `pitch_est`, `pitch_gt`, `yaw_est`, `yaw_gt`

  