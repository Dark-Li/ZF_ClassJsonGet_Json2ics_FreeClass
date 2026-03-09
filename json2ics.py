import json
from datetime import datetime, timedelta
import uuid
import os
from config import SEMESTER_START_DATETIME

# ==============================
# 配置区
# ==============================
json_folder = "json_input"   # 存放 JSON 文件的文件夹
ics_folder = "ics_output"    # 输出 ICS 文件的文件夹
semester_start = SEMESTER_START_DATETIME  # 学期第一周周一
timezone = "Asia/Shanghai"

# 每节课对应的时间
session_times = {
    1: ("08:00", "08:45"),
    2: ("08:55", "09:40"),
    3: ("10:00", "10:45"),
    4: ("10:55", "11:40"),
    5: ("13:00", "13:45"),
    6: ("13:55", "14:40"),
    7: ("14:50", "15:35"),
    8: ("15:45", "16:30"),
    9: ("16:40", "17:25"),
    10: ("17:35", "18:20"),
    11: ("18:30", "19:15"),
    12: ("19:25", "20:10"),
}

# ==============================
# 工具函数
# ==============================
def get_datetime_for_course(week, weekday, session):
    """根据周数、星期、节数计算具体日期和时间"""
    day = semester_start + timedelta(weeks=week-1, days=weekday-1)
    start_time_str, end_time_str = session_times[session]
    start_dt = datetime.strptime(f"{day.date()} {start_time_str}", "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(f"{day.date()} {end_time_str}", "%Y-%m-%d %H:%M")
    return start_dt, end_dt

def format_datetime(dt):
    """格式化为ICS标准时间格式"""
    return dt.strftime("%Y%m%dT%H%M%S")

def generate_uid():
    """生成唯一UID"""
    return uuid.uuid4().hex

def generate_ics_from_json(json_path, ics_path):
    """根据单个 JSON 文件生成 ICS 文件"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    courses = data["data"]["courses"]

    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GYSL//Ender//ZF-Class-ICS//EN",
        "CALSCALE:GREGORIAN"
    ]

    for course in courses:
        title = course["title"]
        location = course["place"]
        teacher = course["teacher"]
        credit = course.get("credit", "")
        weekday = course["weekday"]  # 1=周一
        list_sessions = course["list_sessions"]
        list_weeks = course["list_weeks"]

        for week in list_weeks:
            for session in list_sessions:
                start_dt, end_dt = get_datetime_for_course(week, weekday, session)
                dtstamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
                uid = generate_uid()
                description = f"1. 任课教师: {teacher}\\n2. 课程属性: 必修\\n3. 学分: {credit}\\n4. 属于系统课程: 否"

                ics_content.extend([
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{dtstamp}",
                    f"DTSTART;TZID={timezone}:{format_datetime(start_dt)}",
                    f"DTEND;TZID={timezone}:{format_datetime(end_dt)}",
                    f"SUMMARY:{title}",
                    f"DESCRIPTION:{description}",
                    f"LOCATION:{location}",
                    "BEGIN:VALARM",
                    "ACTION:AUDIO",
                    "TRIGGER:-PT30M",
                    f"DESCRIPTION:{title} 即将开始",
                    "END:VALARM",
                    "END:VEVENT"
                ])

    ics_content.append("END:VCALENDAR")

    # 写入 ICS 文件
    with open(ics_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ics_content))

# ==============================
# 批量处理文件夹
# ==============================
if not os.path.exists(ics_folder):
    os.makedirs(ics_folder)

for filename in os.listdir(json_folder):
    if filename.lower().endswith(".json"):
        json_path = os.path.join(json_folder, filename)
        ics_filename = os.path.splitext(filename)[0] + ".ics"
        ics_path = os.path.join(ics_folder, ics_filename)
        generate_ics_from_json(json_path, ics_path)
        print(f"生成 ICS: {ics_filename}")

print("全部完成！")
