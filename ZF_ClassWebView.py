from flask import render_template, request
import os
import datetime
from icalendar import Calendar
from config import SEMESTER_START_DATE

# 课程时间段定义
CLASS_TIME_SLOTS = [
    ("第1-2节", (8, 0), (9, 40)),
    ("第3-4节", (10, 0), (11, 40)),
    ("第5-6节", (13, 0), (14, 40)),
    ("第7-8节", (14, 50), (16, 30)),
    ("第9-10节", (16, 40), (18, 20)),
    ("第11-12节", (18, 30), (20, 10))
]

# 解析ics文件的函数
def parse_ics_file(file_path):
    with open(file_path, 'rb') as f:
        cal = Calendar.from_ical(f.read())
    events = []
    for component in cal.walk():
        if component.name == "VEVENT":
            event = {
                'summary': str(component.get('summary', '')),
                'start': component.get('dtstart').dt,
                'end': component.get('dtend').dt
            }
            events.append(event)
    return events

# 全局缓存，存储解析后的课程信息
users_courses_cache = None

# 获取所有人的课程信息
def get_all_users_courses():
    global users_courses_cache
    if users_courses_cache is None:
        ics_dir = "ics_output"
        users_courses_cache = {}
        for filename in os.listdir(ics_dir):
            if filename.endswith('.ics'):
                user_name = filename.split('.')[0]
                file_path = os.path.join(ics_dir, filename)
                users_courses_cache[user_name] = parse_ics_file(file_path)
    return users_courses_cache

# 计算指定日期和时间段的空课程人员
def get_free_users(date, time_slot):
    users_courses = get_all_users_courses()
    free_users = []
    
    # 解析时间段
    slot_name, start_time, end_time = time_slot
    slot_start = datetime.datetime.combine(date, datetime.time(*start_time))
    slot_end = datetime.datetime.combine(date, datetime.time(*end_time))
    
    for user, courses in users_courses.items():
        is_free = True
        for course in courses:
            course_start = course['start']
            course_end = course['end']
            
            # 处理时区问题，统一转换为不带时区的datetime
            if hasattr(course_start, 'tzinfo') and course_start.tzinfo is not None:
                course_start = course_start.replace(tzinfo=None)
            if hasattr(course_end, 'tzinfo') and course_end.tzinfo is not None:
                course_end = course_end.replace(tzinfo=None)
            
            # 检查课程是否与当前时间段重叠
            if (course_start < slot_end) and (course_end > slot_start):
                is_free = False
                break
        if is_free:
            free_users.append(user)
    return free_users

# 计算当前周数（根据学期开始日期计算）
def get_current_week():
    semester_start = SEMESTER_START_DATE
    today = datetime.date.today()
    # 计算当前周数
    delta = today - semester_start
    week_num = delta.days // 7 + 1
    return max(1, week_num)

# 获取指定周的所有日期（周一到周日）
def get_week_dates(week_num):
    base_date = SEMESTER_START_DATE
    start_date = base_date + datetime.timedelta(weeks=week_num-1)
    week_dates = []
    for i in range(7):
        week_dates.append(start_date + datetime.timedelta(days=i))
    return week_dates

# 获取指定周的整体空课程情况
def get_week_free_users(week_num):
    week_dates = get_week_dates(week_num)
    week_free_users = {}
    
    for date in week_dates:
        day_free_users = {}
        for time_slot in CLASS_TIME_SLOTS:
            day_free_users[time_slot[0]] = get_free_users(date, time_slot)
        week_free_users[date] = day_free_users
    
    return week_free_users

def index():
    current_week = get_current_week()
    selected_week = current_week
    selected_date = datetime.date.today()
    selected_time_slot = CLASS_TIME_SLOTS[0]
    view_mode = 'week'  # 默认周视图
    
    if request.method == 'POST':
        if 'view_mode' in request.form:
            view_mode = request.form['view_mode']
        
        if view_mode == 'week':
            if 'week_num' in request.form:
                selected_week = int(request.form['week_num'])
        else:
            if 'date' in request.form:
                date_str = request.form['date']
                selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if 'time_slot' in request.form:
                slot_index = int(request.form['time_slot'])
                selected_time_slot = CLASS_TIME_SLOTS[slot_index]
    
    # 获取周视图数据
    week_dates = get_week_dates(selected_week)
    week_free_users = get_week_free_users(selected_week)
    
    # 获取日视图数据
    day_free_users = {}
    if view_mode == 'day':
        for time_slot in CLASS_TIME_SLOTS:
            day_free_users[time_slot[0]] = get_free_users(selected_date, time_slot)
    
    # 获取特定日期和时间段的空课程人员
    specific_free_users = []
    if view_mode == 'specific':
        specific_free_users = get_free_users(selected_date, selected_time_slot)
    
    return render_template('ZF_ClassWebView.html',
                           current_week=current_week,
                           selected_week=selected_week,
                           selected_date=selected_date,
                           selected_time_slot=selected_time_slot,
                           class_time_slots=CLASS_TIME_SLOTS,
                           view_mode=view_mode,
                           week_dates=week_dates,
                           week_free_users=week_free_users,
                           day_free_users=day_free_users,
                           specific_free_users=specific_free_users)


       