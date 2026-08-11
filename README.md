# 课堂轻松点名助手

> Ciallo～(∠・ω< )⌒☆ 一款专为课堂设计的轻量级随机点名工具，支持多种点名模式与个性化设置。

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [安装与运行](#安装与运行)
- [使用指南](#使用指南)
- [配置文件说明](#配置文件说明)
- [快捷键](#快捷键)
- [数据存储](#数据存储)
- [常见问题](#常见问题)
- [开发者信息](#开发者信息)
- [许可证](#许可证)

---

## 项目简介

**课堂轻松点名助手**是一款基于 Python + tkinter 开发的桌面应用程序，专为教师和课堂场景设计。它提供了丰富的点名模式（普通、精简、公平、连抽、特效、极小化），支持语音播报、权重调整、历史记录等实用功能，让课堂互动更加轻松有趣。

本软件由 **陈恩祈 (Chenenqi)** 开发，采用 MIT 开源协议。

---

## 功能特性

- **六种点名模式**：普通模式、精简模式、公平模式、连抽模式、特效模式、极小化模式，适应不同课堂场景
- **权重随机抽取**：可为每位学生单独设置被抽中权重（0.1~10.0），实现差异化概率控制
- **语音播报**：支持 TTS 语音朗读被点中姓名（可开关）
- **历史记录**：自动保存点名与抽组记录，支持查看历史
- **公平模式**：每人抽中一次后才重复，确保公平性
- **连抽模式**：支持五连抽、十连抽，结果汇总展示
- **极小化挂件**：悬浮小窗口，适合 PPT 全屏时使用
- **快捷键支持**：F2 点名、F3 抽组、Ctrl+M 最小化
- **数据持久化**：学生名单、小组名单、历史记录、权重设置等自动保存
- **单实例运行**：通过端口绑定确保同时只运行一个实例
- **个性化设置**：背景色、文字色、按钮色、字体、窗口尺寸等均可自定义

---

## 安装与运行

### 方式一：直接运行（推荐）

如果您已获取 `课堂轻松点名助手.exe` 可执行文件，只需**双击运行**即可，无需安装任何 Python 环境或依赖库。

- 下载后，将 `.exe` 文件放在您希望存放的目录下（建议新建一个独立文件夹）
- 双击 `课堂轻松点名助手.exe` 启动程序
- 所有配置文件（`*.dat`）将自动生成在 `.exe` 所在目录

> 注意：首次运行可能被 Windows Defender 或杀毒软件拦截，请选择"仍要运行"或添加信任。本软件为开源项目，无任何恶意代码，可放心使用。

### 方式二：从源码运行（适用于开发者）

#### 环境要求

- Python 3.6 或更高版本
- 依赖库：`tkinter`（内置）、`pyttsx3`（语音播报）、`openpyxl`（Excel 导入，可选）、`keyboard`（热键，可选）

#### 安装依赖

```bash
pip install pyttsx3 openpyxl keyboard
```

#### 运行方式

```bash
python call.py
```

#### 打包为独立可执行文件（可选）

使用 PyInstaller 打包：

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "课堂轻松点名助手" call.py
```

---

## 使用指南

### 首次启动

- 程序启动后默认进入**普通模式**
- 默认内置 8 名学生（张三、李四、王五等）和 4 个小组（第一组～第四组）
- 管理员初始密码：`114514`

### 模式切换

通过菜单栏「设置」→「模式选择」切换模式，切换后程序会自动重启：

| 模式 | 说明 |
|------|------|
| 普通模式 | 完整功能：点名、抽组、五连抽、十连抽 |
| 精简模式 | 仅保留点名和抽组，界面更简洁 |
| 公平模式 | 每人被抽中一次后才进入下一轮，需确认名单 |
| 连抽模式 | 专用连抽页面，结果汇总展示 |
| 特效模式 | 全屏 Emoji 飘动特效展示被点中姓名 |
| 极小化模式 | 悬浮小挂件，适合 PPT 全屏时使用 |

### 导入名单

通过菜单「文件」→「导入名单」支持：
- **TXT 文件**：每行一个姓名，自动识别 UTF-8/GBK/GB2312 编码
- **Excel 文件**：支持 `.xlsx` / `.xls` 格式，读取第一个工作表的所有非空单元格

### 编辑名单

通过菜单「文件」→「编辑名单」可同时编辑学生名单和小组名单（需要管理员密码验证）

### 权重设置

通过菜单「设置」→「权重设置」可为每位学生设置个性化权重（0.1~10.0），权重越高被抽中概率越大

### 语音播报与停留时间

- 通过菜单「设置」→「语音播报」可开关 TTS 语音功能
- 通过菜单「设置」→「停留时间」可调整结果展示时长（500~10000 毫秒）

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `F2` | 随机点名 |
| `F3` | 随机抽组 |
| `Ctrl+M` | 最小化至悬浮球（双击悬浮球恢复窗口） |

> 注意：快捷键依赖 `keyboard` 库，可能需要管理员权限。直接运行 `.exe` 版本时已内置该支持。

---

## 配置文件说明

程序运行时会自动在可执行文件所在目录生成以下数据文件：

| 文件名 | 说明 |
|--------|------|
| `students.dat` | 学生名单（加密存储） |
| `groups.dat` | 小组名单（加密存储） |
| `history.dat` | 点名历史记录 |
| `fair_history.dat` | 公平模式历史记录 |
| `weights.dat` | 学生权重配置 |
| `config.dat` | 程序个性化设置 |

所有 `.dat` 文件均采用 XOR 异或加密，保证数据安全性。

---

## 常见问题

**Q：程序提示「程序已在运行，退出当前实例」怎么办？**

A：程序通过绑定本地端口 52077 确保单实例运行。如需强制启动新实例，请先关闭已运行的进程。

**Q：语音播报没有声音？**

A：请确认系统音频设备正常工作，且已安装 `pyttsx3` 库（源码运行）；直接运行 `.exe` 版本已集成该功能。

**Q：导入 Excel 文件失败？**

A：请确保已安装 `openpyxl` 库：`pip install openpyxl`；`.exe` 版本已内置支持。

**Q：快捷键无效？**

A：快捷键功能依赖 `keyboard` 库，在某些系统上可能需要管理员权限运行。如无法使用，可通过界面按钮操作。

**Q：如何重置管理员密码？**

A：删除 `config.dat` 文件后重启程序，密码将恢复为初始值 `114514`。

**Q：`.exe` 文件被 Windows 识别为病毒？**

A：这是 PyInstaller 打包程序的常见误报，请添加信任或暂时关闭实时保护。您也可以通过源码运行方式避免此问题。

---

## 开发者信息

- **开发者**：陈恩祈 (Chenenqi)
- **联系方式**：GitHub @ranxiruo（如有问题欢迎提 Issue）
- **开发语言**：Python 3
- **GUI 框架**：tkinter
- **开源协议**：MIT License

---

## 许可证

本项目采用 MIT 许可证。你可以自由使用、修改、分发本软件，但需保留版权声明。

```
MIT License

Copyright (c) 2026 Chenenqi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

> Ciallo～(∠・ω< )⌒☆ 愿每一次点名都充满惊喜与欢笑！
