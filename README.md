# 正方教务系统课程表管理系统

## 项目介绍

正方教务系统课程表管理系统是一个用于获取、转换和管理课程表的工具集，支持从正方教务系统获取课程表、转换为ICS日历格式、统计和查询空课程情况。

## 功能特点

- **课程表获取**：通过学号密码从教务系统获取课程表，并保存为JSON格式
- **课程表转换**：将JSON格式课程表转换为ICS日历格式，可导入到各种日历应用
- **空课程查询**：查询不同时间段的空课程情况，支持周视图、日视图和特定查询
- **空课程统计**：生成Excel格式的空课程统计表

## 项目结构

```
ZF_ClassJsonGet_Json2ics_FreeClass/
├── app.py              # 主应用文件，整合所有功能
├── GetJsonClass.py     # 课程表获取功能
├── ZF_ClassWebView.py  # 空课程查询功能
├── json2ics.py         # 课程表转换功能
├── 统计空课表.py         # 空课程统计功能
├── config.py           # 配置文件，统一管理学期开始日期
├── requirements.txt    # 依赖文件
├── Dockerfile          # Docker构建文件
├── docker-compose.yml  # Docker Compose配置文件
├── templates/          # HTML模板文件
│   ├── index.html      # 主页面
│   ├── GetJsonClass.html  # 课程表获取页面
│   ├── json2ics.html   # 课程表转换页面
│   └── ZF_ClassWebView.html  # 空课程查询页面
├── json_input/         # 存放JSON格式课程表
├── ics_output/         # 存放ICS格式日历文件
└── 空课表统计结果Excel/  # 存放空课程统计表
```

## 技术栈

- Python 3.9+
- Flask 3.0.0
- icalendar 5.0.10
- openpyxl 3.1.5
- requests 2.31.0
- pyquery 2.0.0
- rsa 4.9

## 安装部署

### 方法一：本地运行

1. **克隆项目**
   ```bash
   git clone <项目地址>
   cd ZF_ClassJsonGet_Json2ics_FreeClass
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   ```

3. **激活虚拟环境**
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

5. **运行应用**
   ```bash
   python app.py
   ```

6. **访问应用**
   打开浏览器，访问 `http://localhost:5000`

### 方法二：Docker部署

1. **安装Docker和Docker Compose**
   请参考官方文档安装Docker和Docker Compose

2. **克隆项目**
   ```bash
   git clone <项目地址>
   cd ZF_ClassJsonGet_Json2ics_FreeClass
   ```

3. **构建并启动容器**
   ```bash
   docker-compose up -d
   ```

4. **访问应用**
   打开浏览器，访问 `http://localhost:5000`

## 使用方法

### 1. 课程表获取

1. 在主页面点击「课程表获取」
2. 输入学号和密码
3. 点击「获取课程表」按钮
4. 系统会自动从教务系统获取课程表并保存为JSON格式

### 2. 课程表转换与统计

1. 在主页面点击「课程表转换与统计」
2. 点击「将JSON转换为ICS」按钮，将JSON格式课程表转换为ICS日历格式
3. 点击「生成空课程统计表」按钮，生成Excel格式的空课程统计表
4. 可以下载生成的ICS文件和Excel文件

### 3. 空课程查询

1. 在主页面点击「空课程查询」
2. 选择视图模式：周视图、日视图或特定查询
3. 根据选择的视图模式，选择相应的参数（周数、日期、时间段等）
4. 点击「查询」按钮，查看空课程情况

## 配置说明

项目的配置文件为 `config.py`，主要配置项：

```python
import datetime

SEMESTER_START_DATE = datetime.date(2026, 3, 2)  # 学期第一周周一（date类型）
SEMESTER_START_DATETIME = datetime.datetime(2026, 3, 2, 0, 0, 0)  # 学期第一周周一（datetime类型）
```

如果需要修改学期开始日期，只需要修改 `config.py` 文件中的日期即可。

## 注意事项

1. 本系统需要从教务系统获取课程表，因此需要有效的学号和密码
2. 生成的ICS文件可以导入到各种日历应用（如Google日历、Outlook等）
3. 空课程查询功能需要先获取课程表并转换为ICS格式
4. 首次使用时，需要先获取课程表，然后转换为ICS格式，才能使用空课程查询和统计功能

## 项目维护

- **依赖更新**：修改 `requirements.txt` 文件后，重新安装依赖
- **Docker镜像更新**：修改代码后，运行 `docker-compose up -d --build` 重新构建镜像
- **数据备份**：定期备份 `json_input`、`ics_output` 和 `空课表统计结果Excel` 目录中的数据

## 许可证

本项目仅供学习和研究使用，不得用于商业用途。

## 联系方式

如有问题或建议，请联系项目维护者。