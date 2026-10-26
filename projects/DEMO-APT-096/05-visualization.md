# 同源模型与空间表现

当前设计v1.1。`visuals/render-input.json`是渲染时冻结的项目数据，`visuals/render-manifest.json`保存模型输入SHA-256、三个相机的位置/目标、渲染引擎及采样设置。

| 视图 | 文件 | 用途 |
|---|---|---|
| 总体轴测 | visuals/01-axon.png | 核对房间关系、家具落位、通道及门窗 |
| 客厅透视 | visuals/02-living.png | 表达朝向西侧实墙的会客区、浅木和米白材料 |
| 书房透视 | visuals/03-study.png | 表达工作台、书柜与临时客用家具的关系 |

源场景为`visuals/qimu-home.blend`，交换模型为`visuals/qimu-home.glb`。场景用Blender/Cycles CPU渲染，32 samples、1600×1060px；轴测将墙体切至1050mm，透视保留完整墙体。图像来自几何与材质模型，家具采用设计体量表达。

已逐张查看三幅图，核对总体房间关系、南北窗及入口、最终客厅朝向、书房工作台和柜体，以及原木/米白/绿灰配色。相机、家具尺寸和开口来自同一数据；ISS03修订后的客厅朝向已经同步。模型与冻结输入哈希一致性见`state/artifact-check.json`。

这一步完成空间表现与设计核对，未发生客户签样或采购确认。实际产品造型与表面质感在选型后继续深化。
