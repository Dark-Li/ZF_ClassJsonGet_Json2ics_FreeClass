import base64
import binascii
import json
import re
import os
import time
import traceback
import sys
import unicodedata
import urllib3
from urllib.parse import urljoin

import requests
import rsa
from pyquery import PyQuery as pq
from requests import exceptions

RASPIANIE = [
    ["8:00", "8:40"],
    ["8:00", "8:45"],
    ["8:55", "9:40"],
    ["10:00", "10:45"],
    ["10:55", "11:40"],
    ["13:00", "13:45"],
    ["13:55", "14:40"],
    ["14:50", "15:35"],
    ["15:45", "16:30"],
    ["16:40", "17:25"],
    ["17:35", "18:20"],
    ["18:30", "19:15"],
    ["19:25", "20:10"],
]

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Client:
    raspisanie = []
    ignore_type = []
    def __init__(self, cookies={}, **kwargs):
        # 基础配置
        self.base_url = kwargs.get("base_url")
        self.raspisanie = kwargs.get("raspisanie", RASPIANIE)
        self.ignore_type = kwargs.get("ignore_type", [])
        self.detail_category_type = kwargs.get("detail_category_type", [])
        self.timeout = kwargs.get("timeout", 3)
        Client.raspisanie = self.raspisanie
        Client.ignore_type = self.ignore_type

        self.key_url = urljoin(self.base_url, "/xtgl/login_getPublicKey.html")
        self.login_url = urljoin(self.base_url, "/xtgl/login_slogin.html")
        self.kaptcha_url = urljoin(self.base_url, "/kaptcha")
        self.headers = requests.utils.default_headers()
        self.headers["Referer"] = self.login_url
        self.headers[
            "User-Agent"
        ] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36"
        self.headers[
            "Accept"
        ] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3"
        self.sess = requests.Session()
        self.sess.keep_alive = False
        self.sess.verify = False
        self.cookies = cookies

    def login(self, sid, password):
        """登录教务系统"""
        need_verify = False
        try:
            # 登录页
            req_csrf = self.sess.get(
                self.login_url, headers=self.headers, timeout=self.timeout
            )
            if req_csrf.status_code != 200:
                return {"code": 2333, "msg": "教务系统挂了"}
            # 获取csrf_token
            doc = pq(req_csrf.text)
            csrf_token = doc("#csrftoken").attr("value")
            pre_cookies = self.sess.cookies.get_dict()
            # 获取publicKey并加密密码
            req_pubkey = self.sess.get(
                self.key_url, headers=self.headers, timeout=self.timeout
            ).json()
            modulus = req_pubkey["modulus"]
            exponent = req_pubkey["exponent"]
            if str(doc("input#yzm")) == "":
                # 不需要验证码
                encrypt_password = self.encrypt_password(password, modulus, exponent)
                # 登录数据
                login_data = {
                    "csrftoken": csrf_token,
                    "yhm": sid,
                    "mm": encrypt_password,
                }
                # 请求登录
                req_login = self.sess.post(
                    self.login_url,
                    headers=self.headers,
                    data=login_data,
                    timeout=self.timeout,
                )
                doc = pq(req_login.text)
                tips = doc("p#tips")
                if str(tips) != "":
                    if "用户名或密码" in tips.text():
                        return {"code": 1002, "msg": "用户名或密码不正确"}
                    return {"code": 998, "msg": tips.text()}
                self.cookies = self.sess.cookies.get_dict()
                return {"code": 1000, "msg": "登录成功", "data": {"cookies": self.cookies}}
            # 需要验证码，返回相关页面验证信息给用户，TODO: 增加更多验证方式
            need_verify = True
            req_kaptcha = self.sess.get(
                self.kaptcha_url, headers=self.headers, timeout=self.timeout
            )
            kaptcha_pic = base64.b64encode(req_kaptcha.content).decode()
            return {
                "code": 1001,
                "msg": "获取验证码成功",
                "data": {
                    "sid": sid,
                    "csrf_token": csrf_token,
                    "cookies": pre_cookies,
                    "password": password,
                    "modulus": modulus,
                    "exponent": exponent,
                    "kaptcha_pic": kaptcha_pic,
                    "timestamp": time.time(),
                },
            }
        except exceptions.Timeout:
            msg = "获取验证码超时" if need_verify else "登录超时"
            return {"code": 1003, "msg": msg}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "请重试，若多次失败可能是系统错误维护或需更新接口"}
        except Exception as e:
            traceback.print_exc()
            msg = "获取验证码时未记录的错误" if need_verify else "登录时未记录的错误"
            return {"code": 999, "msg": f"{msg}：{str(e)}"}

    def login_with_kaptcha(
        self, sid, csrf_token, cookies, password, modulus, exponent, kaptcha, **kwargs
    ):
        """需要验证码的登陆"""
        try:
            encrypt_password = self.encrypt_password(password, modulus, exponent)
            login_data = {
                "csrftoken": csrf_token,
                "yhm": sid,
                "mm": encrypt_password,
                "yzm": kaptcha,
            }
            req_login = self.sess.post(
                self.login_url,
                headers=self.headers,
                cookies=cookies,
                data=login_data,
                timeout=self.timeout,
            )
            if req_login.status_code != 200:
                return {"code": 2333, "msg": "教务系统挂了"}
            # 请求登录
            doc = pq(req_login.text)
            tips = doc("p#tips")
            if str(tips) != "":
                if "验证码" in tips.text():
                    return {"code": 1004, "msg": "验证码输入错误"}
                if "用户名或密码" in tips.text():
                    return {"code": 1002, "msg": "用户名或密码不正确"}
                return {"code": 998, "msg": tips.text()}
            self.cookies = self.sess.cookies.get_dict()
            # 不同学校系统兼容差异
            if not self.cookies.get("route"):
                route_cookies = {
                    "JSESSIONID": self.cookies["JSESSIONID"],
                    "route": cookies["route"],
                }
                self.cookies = route_cookies
            else:
                return {"code": 1000, "msg": "登录成功", "data": {"cookies": self.cookies}}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "登录超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "请重试，若多次失败可能是系统错误维护或需更新接口"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "验证码登录时未记录的错误：" + str(e)}

    def get_info(self):
        """获取个人信息"""
        url = urljoin(self.base_url, "/xsxxxggl/xsxxwh_cxCkDgxsxx.html?gnmkdm=N100801")
        try:
            req_info = self.sess.get(
                url,
                headers=self.headers,
                cookies=self.cookies,
                timeout=self.timeout,
            )
            if req_info.status_code != 200:
                return {"code": 2333, "msg": "教务系统挂了"}
            doc = pq(req_info.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            info = req_info.json()
            if info is None:
                return self._get_info()
            result = {
                "sid": info.get("xh"),
                "name": info.get("xm"),
                "college_name": info.get("zsjg_id", info.get("jg_id")),
                "major_name": info.get("zszyh_id", info.get("zyh_id")),
                "class_name": info.get("bh_id", info.get("xjztdm")),
                "status": info.get("xjztdm"),
                "enrollment_date": info.get("rxrq"),
                "candidate_number": info.get("ksh"),
                "graduation_school": info.get("byzx"),
                "domicile": info.get("jg"),
                "postal_code": info.get("yzbm"),
                "politics_status": info.get("zzmmm"),
                "nationality": info.get("mzm"),
                "education": info.get("pyccdm"),
                "phone_number": info.get("sjhm"),
                "parents_number": info.get("gddh"),
                "email": info.get("dzyx"),
                "birthday": info.get("csrq"),
                "id_number": info.get("zjhm"),
            }
            return {"code": 1000, "msg": "获取个人信息成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取个人信息超时"}
        except (
                exceptions.RequestException,
                json.decoder.JSONDecodeError,
                AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "请重试，若多次失败可能是系统错误维护或需更新接口"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取个人信息时未记录的错误：" + str(e)}

    def get_schedule(self, year: int, term: int):
        """获取课程表信息"""
        url = urljoin(self.base_url, "/kbcx/xskbcx_cxXsKb.html?gnmkdm=N2151")
        temp_term = term
        term = term**2 * 3
        data = {"xnm": str(year), "xqm": str(term)}
        try:
            req_schedule = self.sess.post(
                url,
                headers=self.headers,
                data=data,
                cookies=self.cookies,
                timeout=self.timeout,
            )
            if req_schedule.status_code != 200:
                return {"code": 2333, "msg": "教务系统挂了"}
            doc = pq(req_schedule.text)
            if doc("h5").text() == "用户登录":
                return {"code": 1006, "msg": "未登录或已过期，请重新登录"}
            schedule = req_schedule.json()
            if not schedule.get("kbList"):
                return {"code": 1005, "msg": "获取内容为空"}
            result = {
                "sid": schedule["xsxx"].get("XH"),
                "name": schedule["xsxx"].get("XM"),
                "year": year,
                "term": temp_term,
                "count": len(schedule["kbList"]),
                "courses": [
                    {
                        "course_id": i.get("kch_id"),
                        "title": i.get("kcmc"),
                        "teacher": i.get("xm"),
                        "class_name": i.get("jxbmc"),
                        "credit": self.align_floats(i.get("xf")),
                        "weekday": self.parse_int(i.get("xqj")),
                        "time": self.display_course_time(i.get("jc")),
                        "sessions": i.get("jc"),
                        "list_sessions": self.list_sessions(i.get("jc")),
                        "weeks": i.get("zcd"),
                        "list_weeks": self.list_weeks(i.get("zcd")),
                        "evaluation_mode": i.get("khfsmc"),
                        "campus": i.get("xqmc"),
                        "place": i.get("cdmc"),
                        "hours_composition": i.get("kcxszc"),
                        "weekly_hours": self.parse_int(i.get("zhxs")),
                        "total_hours": self.parse_int(i.get("zxs")),
                    }
                    for i in schedule["kbList"]
                ],
                "extra_courses": [i.get("qtkcgs") for i in schedule.get("sjkList")],
            }
            result = self.split_merge_display(result)
            return {"code": 1000, "msg": "获取课表成功", "data": result}
        except exceptions.Timeout:
            return {"code": 1003, "msg": "获取课表超时"}
        except (
            exceptions.RequestException,
            json.decoder.JSONDecodeError,
            AttributeError,
        ):
            traceback.print_exc()
            return {"code": 2333, "msg": "请重试，若多次失败可能是系统错误维护或需更新接口"}
        except Exception as e:
            traceback.print_exc()
            return {"code": 999, "msg": "获取课表时未记录的错误：" + str(e)}

    @classmethod
    def encrypt_password(cls, pwd, n, e):
        """对密码base64编码"""
        message = str(pwd).encode()
        rsa_n = binascii.b2a_hex(binascii.a2b_base64(n))
        rsa_e = binascii.b2a_hex(binascii.a2b_base64(e))
        key = rsa.PublicKey(int(rsa_n, 16), int(rsa_e, 16))
        encropy_pwd = rsa.encrypt(message, key)
        result = binascii.b2a_base64(encropy_pwd)
        return result

    @classmethod
    def parse_int(cls, digits):
        if not digits:
            return None
        if not digits.isdigit():
            return digits
        return int(digits)

    @classmethod
    def align_floats(cls, floats):
        if not floats:
            return None
        if floats == "无":
            return "0.0"
        return format(float(floats), ".1f")

    @classmethod
    def display_course_time(cls, sessions):
        """
        根据课程节数生成上课时间，支持多节连上课
        sessions 示例: "1-2节", "3-8节", "5节"
        """
        if not sessions:
            return None

        # 提取所有节号
        nums = re.findall(r"(\d+)", sessions)
        if not nums:
            return None

        # 将节号转成整数列表
        nums = list(map(int, nums))

        # 找到最早开始节和最晚结束节
        start_index = min(nums)
        end_index = max(nums)

        # 防止索引越界
        if start_index >= len(cls.raspisanie):
            start_index = len(cls.raspisanie) - 1
        if end_index >= len(cls.raspisanie):
            end_index = len(cls.raspisanie) - 1

        start_time = cls.raspisanie[start_index][0]
        end_time = cls.raspisanie[end_index][1]

        return f"{start_time}~{end_time}"

    @classmethod
    def list_sessions(cls, sessions):
        if not sessions:
            return None
        args = re.findall(r"(\d+)", sessions)
        return [n for n in range(int(args[0]), int(args[1]) + 1)]

    @classmethod
    def list_weeks(cls, weeks):
        """返回课程所含周列表"""
        if not weeks:
            return None
        args = re.findall(r"[^,]+", weeks)
        week_list = []
        for item in args:
            if "-" in item:
                weeks_pair = re.findall(r"(\d+)", item)
                if len(weeks_pair) != 2:
                    continue
                if "单" in item:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        if i % 2 == 1:
                            week_list.append(i)
                elif "双" in item:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        if i % 2 == 0:
                            week_list.append(i)
                else:
                    for i in range(int(weeks_pair[0]), int(weeks_pair[1]) + 1):
                        week_list.append(i)
            else:
                week_num = re.findall(r"(\d+)", item)
                if len(week_num) == 1:
                    week_list.append(int(week_num[0]))
        return week_list

    @classmethod
    def get_academia_statistics(cls, display_statistics):
        display_statistics = "".join(display_statistics.split())
        gpa_list = re.findall(r"([0-9]{1,}[.][0-9]*)", display_statistics)
        if len(gpa_list) == 0 or not cls.is_number(gpa_list[0]):
            gpa = None
        else:
            gpa = float(gpa_list[0])
        plan_list = re.findall(
            r"计划总课程(\d+)门通过(\d+)门?.*未通过(\d+)门?.*未修(\d+)?.*在读(\d+)门?.*计划外?.*通过(\d+)门?.*未通过(\d+)门",
            display_statistics,
        )
        if len(plan_list) == 0 or len(plan_list[0]) < 7:
            return {"gpa": gpa}
        plan_list = plan_list[0]
        return {
            "gpa": gpa,  # 平均学分绩点GPA
            "planed_courses": {
                "total": int(plan_list[0]),  # 计划内总课程数
                "passed": int(plan_list[1]),  # 计划内已过课程数
                "failed": int(plan_list[2]),  # 计划内未过课程数
                "missed": int(plan_list[3]),  # 计划内未修课程数
                "in": int(plan_list[4]),  # 计划内在读课程数
            },
            "unplaned_courses": {
                "passed": int(plan_list[5]),  # 计划外已过课程数
                "failed": int(plan_list[6]),  # 计划外未过课程数
            },
        }

    @classmethod
    def get_academia_type_statistics(cls, content: str):
        finder = re.findall(
            r"\"(.*)&nbsp.*要求学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;).*获得学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;).*未获得学分.*:([0-9]{1,}[.][0-9]*|0|&nbsp;)[\s\S]*?<span id='showKc(.*)'></span>",
            content,
        )
        finder_list = list({}.fromkeys(finder).keys())
        academia_list = [
            list(i)
            for i in finder_list
            if i[0] != ""  # 类型名称不为空
            and len(i[0]) <= 20  # 避免正则到首部过长类型名称
            and "span" not in i[-1]  # 避免正则到尾部过长类型名称
            and i[0] not in cls.ignore_type  # 忽略的类型名称
        ]
        result = {
            i[0]: {
                "id": i[-1],
                "credits": {
                    "required": i[1] if cls.is_number(i[1]) and i[1] != "0" else None,
                    "earned": i[2] if cls.is_number(i[2]) and i[2] != "0" else None,
                    "missed": i[3] if cls.is_number(i[3]) and i[3] != "0" else None,
                },
            }
            for i in academia_list
        }
        return result

    @classmethod
    def get_display_term(cls, sid, year, term):
        """
        计算培养方案具体学期转化成中文
        note: 留级和当兵等情况会不准确
        """
        if (sid and year and term) is None:
            return None
        grade = int(sid[0:2])
        year = int(year[2:4])
        term = int(term)
        dict = {
            grade: "大一上" if term == 1 else "大一下",
            grade + 1: "大二上" if term == 1 else "大二下",
            grade + 2: "大三上" if term == 1 else "大三下",
            grade + 3: "大四上" if term == 1 else "大四下",
        }
        return dict.get(year)

    @classmethod
    def split_merge_display(cls, schedule):
        """
        拆分同周同天同课程不同时段数据合并的问题
        """
        repetIndex = []
        count = 0
        for items in schedule["courses"]:
            for index in range(len(schedule["courses"])):
                if (schedule["courses"]).index(items) == count:  # 如果对比到自己就忽略
                    continue
                elif (
                    items["course_id"]
                    == schedule["courses"][index]["course_id"]  # 同周同天同课程
                    and items["weekday"] == schedule["courses"][index]["weekday"]
                    and items["weeks"] == schedule["courses"][index]["weeks"]
                ):
                    repetIndex.append(index)  # 满足条件记录索引
            count += 1  # 记录当前对比课程的索引
        if len(repetIndex) % 2 != 0:  # 暂时考虑一天两个时段上同一门课，不满足条件不进行修改
            return schedule
        for r in range(0, len(repetIndex), 2):  # 索引数组两两成对，故步进2循环
            fir = repetIndex[r]
            sec = repetIndex[r + 1]
            if len(re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])) == 4:
                schedule["courses"][fir]["sessions"] = (
                    re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])[0]
                    + "-"
                    + re.findall(r"(\d+)", schedule["courses"][fir]["sessions"])[1]
                    + "节"
                )
                schedule["courses"][fir]["list_sessions"] = cls.list_sessions(
                    schedule["courses"][fir]["sessions"]
                )
                schedule["courses"][fir]["time"] = cls.display_course_time(
                    schedule["courses"][fir]["sessions"]
                )

                schedule["courses"][sec]["sessions"] = (
                    re.findall(r"(\d+)", schedule["courses"][sec]["sessions"])[2]
                    + "-"
                    + re.findall(r"(\d+)", schedule["courses"][sec]["sessions"])[3]
                    + "节"
                )
                schedule["courses"][sec]["list_sessions"] = cls.list_sessions(
                    schedule["courses"][sec]["sessions"]
                )
                schedule["courses"][sec]["time"] = cls.display_course_time(
                    schedule["courses"][sec]["sessions"]
                )
        return schedule

    @classmethod
    def split_notifications(cls, item):
        if not item.get("xxnr"):
            return {"type": None, "content": None}
        content_list = re.findall(r"(.*):(.*)", item["xxnr"])
        if len(content_list) == 0:
            return {"type": None, "content": item["xxnr"]}
        return {"type": content_list[0][0], "content": content_list[0][1]}

    @classmethod
    def get_place(cls, place):
        return place.split("<br/>")[0] if "<br/>" in place else place

    @classmethod
    def get_course_time(cls, time):
        return "、".join(time.split("<br/>")) if "<br/>" in time else time

    @classmethod
    def is_number(cls, s):
        if s == "":
            return False
        try:
            float(s)
            return True
        except ValueError:
            pass
        try:
            for i in s:
                unicodedata.numeric(i)
            return True
        except (TypeError, ValueError):
            pass
        return False







if __name__ == "__main__":
    from pprint import pprint
    import json
    import base64
    import sys
    import os

    # 读取多账户
    with open("account.json", "r", encoding="utf-8") as f:
        accounts = json.load(f)

    base_url = "https://jxw.sylu.edu.cn"  # 教务系统 URL
    folder = "json_input"
    os.makedirs(folder, exist_ok=True)

    # 遍历每个账户
    for account in accounts:
        sid = account["sid"]
        password = account["password"]

        print(f"正在登录账号：{sid}")

        lgn_cookies = None  # 每次用密码登录
        lgn = Client(lgn_cookies if lgn_cookies is not None else {}, base_url=base_url)

        # 登录
        pre_login = lgn.login(sid, password)
        if pre_login["code"] == 1001:
            pre_dict = pre_login["data"]
            with open(os.path.abspath("temp.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps(pre_dict, ensure_ascii=False, indent=4))
            with open(os.path.abspath("kaptcha.png"), "wb") as pic:
                pic.write(base64.b64decode(pre_dict["kaptcha_pic"]))
            kaptcha = input(f"{sid} 的验证码：")
            result = lgn.login_with_kaptcha(
                pre_dict["sid"],
                pre_dict["csrf_token"],
                pre_dict["cookies"],
                pre_dict["password"],
                pre_dict["modulus"],
                pre_dict["exponent"],
                kaptcha,
            )
            if result["code"] != 1000:
                pprint(result)
                continue  # 登录失败跳过
            lgn_cookies = lgn.cookies
        elif pre_login["code"] == 1000:
            lgn_cookies = lgn.cookies
        else:
            pprint(pre_login)
            continue  # 登录失败跳过

        # 获取个人信息
        self_info = lgn.get_info()
        if self_info["code"] != 1000:
            pprint(self_info)
            continue

        name = self_info["data"]["name"]

        # 获取课程表
        course_json = lgn.get_schedule(2025, 2)
        if course_json["code"] != 1000:
            pprint(course_json)
            continue

        # 保存 JSON 文件
        file_path = os.path.join(folder, f"{name}.json")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(course_json, ensure_ascii=False, indent=4))

        print(f"{sid} ({name}) 的课表已生成：{file_path}\n")