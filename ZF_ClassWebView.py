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
users_courses_cache_signature = None


def _build_ics_signature():
    """构建 ICS 文件快照，用于判断缓存是否需要失效。"""
    ics_dir = "ics_output"
    if not os.path.isdir(ics_dir):
        return tuple()

    signature = []
    for filename in sorted(os.listdir(ics_dir)):
        if not filename.lower().endswith('.ics'):
            continue
        file_path = os.path.join(ics_dir, filename)
        try:
            stat = os.stat(file_path)
        except OSError:
            continue
        signature.append((filename, stat.st_mtime_ns, stat.st_size))

    return tuple(signature)


def invalidate_users_courses_cache():
    """主动清空缓存，供外部流程（如批量转换）调用。"""
    global users_courses_cache, users_courses_cache_signature
    users_courses_cache = None
    users_courses_cache_signature = None


def _normalize_course_datetime(value):
    """统一课程时间为无时区 datetime，避免比较时报错。"""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        value = datetime.datetime.combine(value, datetime.time.min)

    if hasattr(value, 'tzinfo') and value.tzinfo is not None:
        value = value.replace(tzinfo=None)

    return value


def _safe_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_slot_index(index_value):
    return max(0, min(index_value, len(CLASS_TIME_SLOTS) - 1))


def _normalize_slot_range(start_index, end_index):
    start_index = _normalize_slot_index(start_index)
    end_index = _normalize_slot_index(end_index)
    if start_index > end_index:
        start_index, end_index = end_index, start_index
    return start_index, end_index


def get_user_names():
    return sorted(get_all_users_courses().keys())

# 获取所有人的课程信息
def get_all_users_courses():
    global users_courses_cache, users_courses_cache_signature
    current_signature = _build_ics_signature()
    if users_courses_cache is None or users_courses_cache_signature != current_signature:
        users_courses_cache = {}
        ics_dir = "ics_output"
        for filename, _, _ in current_signature:
            user_name = filename.split('.')[0]
            file_path = os.path.join(ics_dir, filename)
            users_courses_cache[user_name] = parse_ics_file(file_path)
        users_courses_cache_signature = current_signature
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
            course_start = _normalize_course_datetime(course['start'])
            course_end = _normalize_course_datetime(course['end'])
            
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


def get_free_users_by_slot_range(date, start_slot_index, end_slot_index):
    start_slot_index, end_slot_index = _normalize_slot_range(start_slot_index, end_slot_index)
    selected_slots = CLASS_TIME_SLOTS[start_slot_index:end_slot_index + 1]
    if not selected_slots:
        return []

    users_order = list(get_all_users_courses().keys())
    free_users_set = None

    for time_slot in selected_slots:
        current_free_users = set(get_free_users(date, time_slot))
        if free_users_set is None:
            free_users_set = current_free_users
        else:
            free_users_set &= current_free_users

    if free_users_set is None:
        return []

    return [user for user in users_order if user in free_users_set]


def get_person_week_courses(user_name, week_num):
    week_dates = get_week_dates(week_num)
    week_dates_set = set(week_dates)
    person_week_courses = {
        date: {slot[0]: [] for slot in CLASS_TIME_SLOTS}
        for date in week_dates
    }

    if not user_name:
        return week_dates, person_week_courses

    users_courses = get_all_users_courses()
    user_courses = users_courses.get(user_name, [])

    for course in user_courses:
        course_start = _normalize_course_datetime(course['start'])
        course_end = _normalize_course_datetime(course['end'])
        course_date = course_start.date()

        if course_date not in week_dates_set:
            continue

        course_name = course.get('summary') or '未命名课程'

        for slot_name, start_time, end_time in CLASS_TIME_SLOTS:
            slot_start = datetime.datetime.combine(course_date, datetime.time(*start_time))
            slot_end = datetime.datetime.combine(course_date, datetime.time(*end_time))

            if (course_start < slot_end) and (course_end > slot_start):
                if course_name not in person_week_courses[course_date][slot_name]:
                    person_week_courses[course_date][slot_name].append(course_name)

    return week_dates, person_week_courses

def index():
    current_week = get_current_week()
    selected_week = current_week
    selected_person_week = current_week
    selected_date = datetime.date.today()
    selected_time_slot = CLASS_TIME_SLOTS[0]
    selected_specific_start_slot_index = 0
    selected_specific_end_slot_index = 0
    user_names = get_user_names()
    selected_user = user_names[0] if user_names else ''
    view_mode = 'week'  # 默认周视图
    
    if request.method == 'POST':
        if 'view_mode' in request.form:
            view_mode = request.form['view_mode']
        
        if view_mode == 'week':
            if 'week_num' in request.form:
                selected_week = _safe_int(request.form['week_num'], selected_week)
        elif view_mode == 'day':
            if 'date' in request.form:
                date_str = request.form['date']
                selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        elif view_mode == 'specific':
            if 'date' in request.form:
                date_str = request.form['date']
                selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if 'specific_start_slot' in request.form or 'specific_end_slot' in request.form:
                selected_specific_start_slot_index = _safe_int(
                    request.form.get('specific_start_slot'),
                    selected_specific_start_slot_index
                )
                selected_specific_end_slot_index = _safe_int(
                    request.form.get('specific_end_slot'),
                    selected_specific_end_slot_index
                )
            elif 'time_slot' in request.form:
                # 兼容旧表单字段：单节次查询等价于起止相同
                slot_index = _safe_int(request.form['time_slot'], 0)
                selected_specific_start_slot_index = slot_index
                selected_specific_end_slot_index = slot_index

            selected_specific_start_slot_index, selected_specific_end_slot_index = _normalize_slot_range(
                selected_specific_start_slot_index,
                selected_specific_end_slot_index
            )
            selected_time_slot = CLASS_TIME_SLOTS[selected_specific_start_slot_index]
        elif view_mode == 'person':
            if 'person_week' in request.form:
                selected_person_week = _safe_int(request.form['person_week'], selected_person_week)
            selected_person_week = max(1, min(selected_person_week, 20))
            selected_user = (request.form.get('person_name') or selected_user).strip()
    
    # 获取周视图数据
    selected_week = max(1, min(selected_week, 20))
    week_dates = get_week_dates(selected_week)
    week_free_users = get_week_free_users(selected_week)
    
    # 获取日视图数据
    day_free_users = {}
    if view_mode == 'day':
        for time_slot in CLASS_TIME_SLOTS:
            day_free_users[time_slot[0]] = get_free_users(selected_date, time_slot)
    
    # 获取特定日期和时间段的空课程人员
    specific_free_users = []
    selected_specific_slot_label = CLASS_TIME_SLOTS[0][0]
    if view_mode == 'specific':
        selected_specific_start_slot_index, selected_specific_end_slot_index = _normalize_slot_range(
            selected_specific_start_slot_index,
            selected_specific_end_slot_index
        )
        selected_specific_start_slot = CLASS_TIME_SLOTS[selected_specific_start_slot_index]
        selected_specific_end_slot = CLASS_TIME_SLOTS[selected_specific_end_slot_index]

        if selected_specific_start_slot_index == selected_specific_end_slot_index:
            selected_specific_slot_label = selected_specific_start_slot[0]
        else:
            selected_specific_slot_label = f"{selected_specific_start_slot[0]} 至 {selected_specific_end_slot[0]}"

        specific_free_users = get_free_users_by_slot_range(
            selected_date,
            selected_specific_start_slot_index,
            selected_specific_end_slot_index
        )

    # 获取个人课表数据
    person_week_dates = []
    person_week_courses = {}
    if view_mode == 'person':
        person_week_dates, person_week_courses = get_person_week_courses(selected_user, selected_person_week)
    
    return render_template('ZF_ClassWebView.html',
                           current_week=current_week,
                           selected_week=selected_week,
                           selected_person_week=selected_person_week,
                           selected_date=selected_date,
                           selected_time_slot=selected_time_slot,
                           selected_specific_start_slot_index=selected_specific_start_slot_index,
                           selected_specific_end_slot_index=selected_specific_end_slot_index,
                           selected_specific_slot_label=selected_specific_slot_label,
                           user_names=user_names,
                           selected_user=selected_user,
                           class_time_slots=CLASS_TIME_SLOTS,
                           view_mode=view_mode,
                           week_dates=week_dates,
                           week_free_users=week_free_users,
                           day_free_users=day_free_users,
                           specific_free_users=specific_free_users,
                           person_week_dates=person_week_dates,
                           person_week_courses=person_week_courses)


       