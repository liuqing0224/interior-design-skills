# 共享项目契约 v2

## 权威文件与编号

`model/project.json`拥有几何、选定方案、材料、家具、灯具、设备和预算输入。Markdown用于解释决策，不另存一套互相冲突的尺寸。

- 项目：project_id、title、revision、input_kind、location_status、units、budget_cny。
- 房间R、墙W、门D、窗WIN、家具F、柜体J、材料M、灯具L、设备E、点位P、需求REQ、问题ISS与变更CHG使用稳定编号。
- 坐标：平面西南内墙角为(0,0)，X向东、Y向北、Z向上；长度mm，角度度，面积㎡，金额CNY。
- 房间`rect=[x,y,w,d]`定义净空间的可计算分区；开放区域边界不自动成为实体墙。
- `envelope=[x,y,w,d]`为内轮廓的包围框。可选`outline=[[x,y],...]`为不重复首点的正交简单多边形，允许凹口、不支持孔洞或斜边；缺省时沿用矩形envelope。面积取实际outline，房间仍须拆为矩形净分区。
- 柜体可设`front_axis=x/y`，明确正面宽度取rect的哪一边。缺省沿用较长边以兼容旧模型；新项目应显式设置。`joinery`可设panel_mm、back_mm、plinth_mm、scribe_mm、bays；自动内净尺寸仅表达该分格的参数条件。
- 地材`pattern.spacing_mm=[x间距,y间距]`控制铺装线，0代表该方向不画线；缺省不推测铺装。`rooms.label_xy`可调整标注位置。可选fixtures含id、room、rect；shower可缺省，不强加示范厨卫设备。
- `drawing.joinery_ids`选择立剖柜体；缺省选投影面积最大的至多3组。完整柜体均列入joinery.csv。
- 家具/柜体`rect`为使用状态外包尺寸；其body表示实体，rug/clearance等辅助对象不计实体碰撞。需要预留的活动范围单独列为`clearances`。
- 墙`axis`、`start/end`、`at`、`thickness`、`height`定义实体，`openings`按墙轴记录起点和宽高、窗台高度。图纸、模型均从同一墙及洞口计算。
- 材料、灯具、设备、家具必须关联有效房间。预算行保留category、basis、quantity、unit、waste、rate、source；未报价单价只能记estimate。

## 状态与来源

输入来源：measured、user_provided、design_assumption、unknown。本示范统一design_assumption，用户选择示范不等于批准全部尺寸。

设计选择：candidate、selected_for_demo、user_approved。不得将selected_for_demo自动升级为用户确认。

专业校核：not_checked、reviewed、needs_input。脚本的计算通过只适用于其明确检查范围。

采购：not_ordered、ordered、received、installed；现场：not_started、in_progress、checked。不根据文件生成自动更新采购/现场状态。

## 变更与交接

执行日志每项含skill、skill_sha256、input_sha256、output_files及哈希、执行时间与结果。只有实际读取并执行的阶段可以记录。

问题至少含id、object_id、observed、basis_type、target、revision、status与recheck_evidence。关闭必须有新版本复查证据。人为注入的测试故障存tests，不能混入项目实际发现。

交付包指向当前模型和实际文件，不混入历史故障图。未实施采购、现场验收和专业审签，状态必须保留。

## 检查适用范围

自动检查支持无孔洞正交轮廓、矩形分区、轴对齐家具及墙、引用、净距和算术；不覆盖任意弧面、不计算结构承载、电气保护或真实管道排水。房间边界不重叠但实体家具可能跨分区，应分别检查。

预算quantity_rule支持floor（materials选择）、net_area、length、projection、count。length/projection按指定家具ids及front_axis计算；count可指定collection=furniture/lights/equipment/points/openings并选择ids，省略ids时计整个集合。明确选择中的未知或重复编号应报错，不能默认为零。

通用二维导出与核验见[工具用法](tool-guide.md)。三维脚本和旧12页汇报仍属于DEMO-APT-096案例流程，不能将二维跨户型验证推及任意三维输入。

设计舒适目标与法规依据必须分列。正式规范应用先核对官方版本、地区、用途和条文；未知阈值不填默认值。
