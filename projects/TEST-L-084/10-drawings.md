# 同源二维图纸

ID-01家具平面、ID-02地材、ID-03灯位分组、ID-04设备条件、ID-05尺寸、ID-06柜体立剖，均读取当前project.json。

总尺寸10500×9000mm、分尺寸、开口编号与宽度从模型推导。房间仍以净矩形分区表达；ID-05红色虚线显示实际L形轮廓。地材分别使用160mm、800×800mm及300×600mm参数，不依赖M01等案例编号。

立剖选择CAB-A、KT-BASE和SIDE-A，显示当前外包尺寸与板厚、背板、踢脚、收口及分格内净宽。其他柜体进入joinery.csv。

图纸在SVG保留data-object、在DXF保留INTERIOR扩展数据对象编号。画幅和图组间距依据图元范围确定；PDF按A3图幅选择比例，图注显示实际比例。室内门窗标注与房间名称的重叠已通过图面检查修正。

生成清单：`drawings/drawing-manifest.json`与`documents/pdf-manifest.json`。导出文件按毫米及模型空间1:1核对。
