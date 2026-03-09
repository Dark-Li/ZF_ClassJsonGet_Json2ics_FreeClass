from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from datetime import datetime

# 导入现有的课程表获取模块
from course_json_out import Client

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于Flash消息

# 教务系统URL配置
BASE_URL = "https://jxw.sylu.edu.cn"  # 替换为实际的教务系统URL

# JSON输出目录
JSON_FOLDER = "json_input"

@app.route('/')
def index():
    return render_template('GetJsonClass.html')

@app.route('/get_schedule', methods=['POST'])
def get_schedule():
    sid = request.form['sid']
    password = request.form['password']
    
    if not sid or not password:
        flash('请输入完整的学号和密码', 'error')
        return redirect(url_for('index'))
    
    try:
        # 创建客户端实例
        lgn = Client(base_url=BASE_URL)
        
        # 登录
        pre_login = lgn.login(sid, password)
        
        if pre_login["code"] == 1001:
            # 需要验证码，目前不支持，返回错误
            flash('登录需要验证码，请使用其他方式获取课程表', 'error')
            return redirect(url_for('index'))
        elif pre_login["code"] == 1000:
            # 登录成功
            lgn_cookies = lgn.cookies
        else:
            # 登录失败
            flash(f'登录失败：{pre_login["msg"]}', 'error')
            return redirect(url_for('index'))
        
        # 获取个人信息
        self_info = lgn.get_info()
        if self_info["code"] != 1000:
            flash(f'获取个人信息失败：{self_info["msg"]}', 'error')
            return redirect(url_for('index'))
        
        name = self_info["data"]["name"]
        
        # 获取当前学年学期
        current_year = datetime.now().year
        current_month = datetime.now().month
        # 8-12月为第一学期，1-7月为第二学期
        current_term = 1 if 8 <= current_month <= 12 else 2
        # 学年为当前年份（第一学期）或当前年份-1（第二学期）
        academic_year = current_year if current_term == 1 else current_year - 1
        
        # 获取课程表
        course_json = lgn.get_schedule(academic_year, current_term)
        if course_json["code"] != 1000:
            flash(f'获取课程表失败：{course_json["msg"]}', 'error')
            return redirect(url_for('index'))
        
        # 保存JSON文件
        file_path = os.path.join(JSON_FOLDER, f"{name}.json")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(course_json, ensure_ascii=False, indent=4))
        
        flash(f'课程表已成功获取并保存，姓名：{name}', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'获取课程表时发生错误：{str(e)}', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # 确保输出目录存在
    os.makedirs(JSON_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)