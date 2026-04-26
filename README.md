# PlotPilot Mobile 手机端适配版

🎉 这个 Fork 增加了完整的手机端适配支持！

## 📱 移动端特性

### 1. 响应式布局
- 侧边栏自动收缩为底部导航栏
- 内容区域自动调整边距
- 支持 iPhone 安全区域（刘海屏适配）

### 2. 触摸优化
- 按钮最小点击区域 44x44px
- 移除 iOS 点击高亮
- 添加触摸反馈动画

### 3. 字体适配
- 输入框字体 16px（防止 iOS 自动缩放）
- 标题字号响应式调整
- 行高优化（1.6-1.8）

### 4. 导航优化
- 底部 Tab 栏（工作台/写作/章节/设置/更多）
- 左侧抽屉菜单（其他功能）
- 支持手势返回

### 5. 暗黑模式
- 自动跟随系统主题
- 底部导航栏暗黑适配
- 卡片和输入框暗黑样式

## 🚀 使用方法

### 方式一：PWA 安装
1. 用手机浏览器访问部署的 PlotPilot
2. 点击"添加到主屏幕"
3. 享受原生应用般的体验

### 方式二：常规访问
直接用手机浏览器访问即可，所有样式会自动适配

## 📐 断点设计

| 设备类型 | 宽度范围 | 布局特点 |
|---------|---------|---------|
| 超小屏 | < 375px | 紧凑间距，小字号 |
| 手机 | 376-768px | 底部导航，单列布局 |
| 平板 | 769-1024px | 双列网格，更大间距 |
| 桌面 | > 1024px | 原桌面布局 |

## 🛠️ 技术实现

### 新增文件
- `frontend/public/mobile-styles.css` - 移动端样式
- `frontend/src/components/layout/MobileLayout.vue` - 移动端布局组件

### 修改文件
- `frontend/index.html` - 添加 viewport 和 PWA meta 标签

### 使用的 CSS 特性
- `env(safe-area-inset-*)` - iPhone 安全区域
- `@media (prefers-color-scheme: dark)` - 系统主题检测
- `@media screen and (max-width: 768px)` - 响应式断点
- `dvh` 单位 - 动态视口高度

## 🔗 相关链接

- 原仓库：https://github.com/shenminglinyi/PlotPilot
- 作者：墨枢

---

Made with 💙 for mobile writers
