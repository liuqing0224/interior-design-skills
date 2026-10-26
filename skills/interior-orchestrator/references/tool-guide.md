# 项目工具

要求Python 3.10+。纯数据、算术与几何检查仅使用标准库；绘图工具另需ezdxf、reportlab、Pillow。

```bash
python skills/interior-orchestrator/scripts/project_tools.py init /path/to/project --name "项目名"
python skills/interior-orchestrator/scripts/project_tools.py check /path/to/project/model/project.json --out /path/to/check.json
python skills/interior-orchestrator/scripts/project_tools.py schedules /path/to/project/model/project.json --out /path/to/schedules
python skills/interior-orchestrator/scripts/project_tools.py record /path/to/project --skill /path/to/skills/interior-brief --outputs 01-brief.md
```

init只写新目录，已有目录拒绝覆盖。check在发现几何、引用、预算或净距问题时返回非零，并输出具体问题。schedules导出房间、材料、灯具、设备、家具与费用表，缺字段会报错，不静默跳过。

record只能用于实际完成的阶段，输出路径需位于项目内、存在且为普通文件；记录输入/技能/输出哈希。工具本身不能证明设计判断正确或批准已经发生。

## 通用二维链路

从同一技能父目录运行（`P`替换为项目目录）：

```bash
python interior-orchestrator/scripts/project_tools.py check P/model/project.json --out P/state/model-check.json
python interior-orchestrator/scripts/project_tools.py schedules P/model/project.json --out P/schedules
python interior-orchestrator/scripts/export_drawings.py P
python interior-orchestrator/scripts/export_pdf.py P --previous P/history/v1.0
python interior-cost/scripts/export_budget.py P
python interior-review/scripts/verify_2d.py P
```

首次无历史版本时省略--previous。PDF需可嵌入中文TrueType字体，设置INTERIOR_PDF_FONT；macOS尝试Arial Unicode。预算入口在临时目录链接已配置的工作区Node依赖，不安装或修改依赖；如自动检测不到，用--node与--modules传入load_workspace_dependencies提供的实际路径。PDF/工作簿作者须先遵守当前环境相应技能的标记约定。

SVG、DXF与PDF共用二维图元。drawing-manifest.json保存来源、生成器哈希、各图原点；柜体用front_axis和joinery参数生成立剖，joinery.csv保存全部柜体。SVG通过data-object、DXF通过INTERIOR扩展数据保留对象编号。

可验证范围为正交简单轮廓与矩形分区。旧render_project.py及tools/build_book.py仍为96㎡住宅案例资源；新项目不要复用其中相机、家具造型或汇报文案。
