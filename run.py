#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Date    : 2018-04-19 19:23:49
# @Author  : kyle (you@example.org)
# @Link    : http://example.org
# @Version : $Id$

import argparse
import datetime
import os
import re
import sys
import logging
import logging.handlers
import time
import random
import requests
from lxml import etree


BASE_DIR = os.path.dirname(os.path.abspath("__file__"))
sys.path.insert(0, BASE_DIR)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36",
    "Host": "pss.txffp.com",
    "Origin": "https://pss.txffp.com",
}
INVOICE_EMAIL = "Example@email.com"
LOG_LEVEL = logging.INFO


with open(os.path.join(BASE_DIR, "cookie.txt"), "r", encoding="utf-8") as f:
    COOKIE = f.read().strip()

REQUEST_DICT = {
    "cookie_dict": {},
    "headers": {},
    "cookie_text": "",
}


class BaseException(Exception):
    pass


class TypeException(BaseException):
    pass


class BaseHandler(object):

    def __init__(self, cookie="", headers=None, req_sleep=False, logger=None, log_level=logging.INFO):
        self.__cookie_dict = {}
        self.__cookie_text = cookie
        self.headers = {}
        self.req_sleep = req_sleep

        if logger is None:
            self.logger = self._logger(log_level)
        else:
            self.logger = logger

        if not headers:
            self._headers = {}
        else:
            self._headers = headers
        self.__init_headers()

    def __cookiedict_update(self):
        """解析文本cookie，并更新cookie字典"""
        if not self.__cookie_text:
            return

        cookie_list = self.__cookie_text.split("; ")
        for kv in cookie_list:
            k, v = kv.split("=")
            self.__cookie_dict[k] = v

    def __cookie_update(self, new_cookie):
        """更新cookie信息"""
        if type(new_cookie) != dict:
            raise TypeException("new cookie必须为字典类型数据")
        self.__cookie_dict.update(new_cookie)

        temp = []
        for k in self.__cookie_dict:
            temp.append("%s=%s" % (k, self.__cookie_dict[k]))
        self.__cookie_text = "; ".join(temp)
        del temp

        self.__flush_headers()

    def __flush_headers(self):
        """刷新请求头"""
        self.headers.update(self._headers)
        self.headers["Cookie"] = self.__cookie_text

    def __init_headers(self):
        # 初始化cookie字典
        self.__cookiedict_update()
        """初始化请求头"""
        self.__flush_headers()
        self.logger.info("初始化请求头...")

    def _logger(self, level=logging.INFO):
        logger = logging.getLogger()
        logger.setLevel(LOG_LEVEL)
        # logger.handlers = []

        ch = logging.StreamHandler()
        # ch.setLevel(LOG_LEVEL)

        fh = logging.handlers.RotatingFileHandler(
                os.path.join(BASE_DIR, "txffp.log"), 
                maxBytes=1024 * 1024 * 1,
                backupCount=5, 
                encoding="utf-8"
            )
        # fh.setLevel(LOG_LEVEL)

        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")

        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        logger.addHandler(ch)
        logger.addHandler(fh)

        return logger

    def set_header(self, key, value):
        """设置或添加键值对到headers中"""
        self.headers[key] = value

    def del_header(self, key):
        """删除headers内的键值对"""
        del self.headers[key]

    def api_handler(self, url, headers="", data="", method="post"):
        if self.req_sleep:
            time.sleep(random.randint(1, 3))
        self.logger.info("请求api接口: %s" % url)
        try:
            if method == "post":
                response = requests.post(url, data, headers=headers)
            elif method == "get":
                response = requests.get(url, headers=headers)
            else:
                raise Exception("错误的或不支持的请求方式[%s]" % method)
        except Exception as e:
            self.logger.error("api接口查询失败(method: %s):\n\turl: %s\n\theaders: %s"
                          "\n\tdata: %s" % (method, url, headers, data, method))
            return

        if response.status_code == 404:
            self.logger.error("得到了一个404响应，可能是cookie没有及时更新导致或者cookie过期等")
            sys.exit("结束程序")

        if response.status_code != 200:
            self.logger.error("api接口信息获取失败(mthod:%s)，状态码: [%s],"
                          "错误信息: [%s]" % (method, response.status_code, response.reason))
            return

        try:
            html_text = response.content.decode("utf-8")
        except UnicodeDecodeError as e:
            self.logger.error("解码api响应内容失败")
            return

        # 更新cookie信息
        self.__cookie_update(response.cookies.get_dict())
        self.logger.info("得到应答")
        return html_text


class APIHandler(BaseHandler):

    APIS = {
        "inv_manage": {
            "url": "https://pss.txffp.com/pss/app/login/invoice/consumeTrans/manage",
            "method": "post",
        },
        "inv_apply": {
            "url": "https://pss.txffp.com/pss/app/login/invoice/consumeTrans/apply",
            "method": "post",
        },
        "inv_subapply": {
            "url": "https://pss.txffp.com/pss/app/login/invoice/consumeTrans/submitApply",
            "method": "post",
        },
        "card_list": {
            "url": "https://pss.txffp.com/pss/app/login/cardList/manage",
            "method": "post",
        },
        "query_card": {
            "url": "https://pss.txffp.com/pss/app/login/invoice/query/card",
            "method": "post",
        },
        "query_apply": {
            "url": "https://pss.txffp.com/pss/app/login/invoice/query/queryApply",
            "method": "post",
        },

    }
    MAX_PAGE_NUM = 6

    def __init__(self, cookie="", headers=None, *args, **kwargs):
        super(APIHandler, self).__init__(cookie, headers, *args, **kwargs)

    def file_write(self, data, filepath):
        with open(filepath, "wb") as f:
            f.write(data)

    def download_handler(self, url, save_path, filename):
        if self.req_sleep:
            time.sleep(random.randint(1, 3))

        self.logger.info("开始下载文件[%s]: %s" % (filename, url))
        try:
            response = requests.get(url, headers=self.headers)
        except Exception as e:
            self.logger.error("文件下载过程中出现异常，url: %s" % url)
            return
        if response.status_code != 200:
            self.logger.error("文件下载失败，状态码: %s" % response.status_code)
            return
        if not response.content:
            self.logger.error("返回内容为空")
            return
        self.file_write(response.content, os.path.join(save_path, filename))

    def api_inv_manage(self, id, month, page_num=1, tradeid_list="", title_id="", invoice_mail="", user_type=""):
        data = {
            "id": id,
            "tradeIdList": tradeid_list,
            "titleId": title_id,
            "invoiceMail": invoice_mail,
            "userType": user_type,
            "month": month,
            "pageNo": page_num,
        }
        self.set_header(
            key="Referer",
            value="https://pss.txffp.com/pss/app/login/invoice/consumeTrans/manage/%s/COMPANY" % id
        )
        return self.api_handler(
            headers=self.headers,
            data=data,
            **self.APIS["inv_manage"],
        )

    def api_inv_apply(self, id, month, tradeid_list, title_id="", invoice_mail="", user_type=""):
        data = {
            "id": id,
            "tradeIdList": ",".join(tradeid_list),
            "titleId": title_id,
            "invoiceMail": invoice_mail,
            "userType": user_type,
            "month": month
        }
        self.set_header(
            key="Referer",
            value="https://pss.txffp.com/pss/app/login/invoice/consumeTrans/manage/%s/COMPANY" % id
        )
        return self.api_handler(
            headers=self.headers,
            data=data,
            **self.APIS["inv_apply"],
        )

    def api_inv_subapply(self, apply_id, id, user_type="COMPANY"):
        data = {
            "applyId": apply_id,
            "id": id,
            "userType": user_type,
        }
        self.set_header(
            key="Referer",
            value="https://pss.txffp.com/pss/app/login/invoice/consumeTrans/manage/%s/COMPANY" % id
        )
        return self.api_handler(
            headers=self.headers,
            data=data,
            **self.APIS["inv_subapply"],
        )

    def api_card_list(self, page_num=1, user_type="COMPANY", type="invoiceApply", change_view="card", query_str=""):
        data = {
            "userType": user_type,
            "type": type,
            "changeView": change_view,
            "queryStr": query_str,
            "pageNo": page_num,
        }
        self.set_header(
            key="Referer",
            value="https://pss.txffp.com/pss/app/login/cardList/manage/invoiceApply/PERSONAL",
        )
        return self.api_handler(
            headers=self.headers,
            data=data,
            **self.APIS["card_list"],
        )

    def api_query_card(self, page_num, user_type="COMPANY", query_str="", change_view="card"):
        data = {
            "userType": user_type,
            "queryStr": query_str,
            "changeView": change_view,
            "pageNo": page_num,
        }
        self.set_header(
            key="Referer",
            value="https://pss.txffp.com/pss/app/login/invoice/query/card/PERSONAL",
        )
        return self.api_handler(
            headers=self.headers,
            data=data,
            **self.APIS["query_card"],
        )

    def api_query_apply(self, card_id, month, page_size=6, user_type="COMPANY", title_name="", station_name=""):
        data = {
            "pageSize": page_size,
            "cardId": card_id,
            "userType": user_type,
            "month": month,
            "titleName": title_name,
            "stationName": station_name,
        }
        self.set_header(
            key="Referer",
            value="https://pss.txffp.com/pss/app/login/invoice/query/queryApply/%s/COMPANY" % card_id
        )
        return self.api_handler(
            headers=self.headers,
            data=data,
            **self.APIS["query_apply"],
        )

    def submit_apply(self, id, month, invoice_mail="", car_num=""):
        self.logger.info("开始对[%s %s]进行开票操作" % (car_num, month))
        page_num = 1
        while True:
            # 开票获取tradeid阶段
            html = self.api_inv_manage(id, month, invoice_mail=invoice_mail)
            if html is None:
                page_num += 1
                continue
            xphtml = etree.HTML(html)

            tradeids = self.__get_tradeid(xphtml)
            if tradeids:
                # 开票获取applyid阶段
                apply_html = self.api_inv_apply(id, month, tradeids, invoice_mail=invoice_mail)
                apply_id, id, user_type = self.__get_applyid(apply_html)
                if not apply_id:
                    self.logger.error("获取apply id信息失败，response: %s" % apply_html)
                # self.logger.info("开票成功（模拟）")
                # 开票最终阶段
                submit_html = self.api_inv_subapply(apply_id, id, user_type)
                with open(os.path.join(BASE_DIR, "submit_html.html"), "w", encoding="utf-8") as f:
                    f.write(submit_html)
                self.logger.info("%s %s 开票结果: %s" %
                             (car_num, month, submit_html.strip()))

            if not self.__has_next_page(xphtml):
                break
            page_num += 1
            if page_num >= self.MAX_PAGE_NUM:
                break

    def submit_apply_all(self, month, invoice_mail="", *args, **kwargs):
        page_num = 1

        while True:
            html = self.api_card_list(page_num, *args, **kwargs)
            if html is None:
                page_num += 1
                continue
            card_list = self.__get_cardid(html)
            if not card_list:
                page_num += 1
                continue

            for cardinfo in card_list:
                self.submit_apply(cardinfo[0], month, car_num=cardinfo[1])

            if not self.__has_next_page(etree.HTML(html)):
                break
            page_num += 1
            if page_num >= self.MAX_PAGE_NUM:
                break

    def inv_download(self, cardid, month, car_num, save_path, page_size=6):
        page_num = 1

        while True:
            # print("第%s页内容" % page_num)
            html = self.api_query_apply(cardid, month, page_size)
            # print(html)
            if html is None:
                page_num += 1
                self.logger.warning("响应数据为空，不执行解析")
                continue
            inv_list = self.__parse_query_apply(html)
            if inv_list:
                for invinfo in inv_list:
                    filename = self.__create_filename(invinfo, car_num)
                    self.download_handler(invinfo["dwurl"], save_path, filename)
            if not self.__has_next_page(etree.HTML(html)):
                self.logger.info("所有分页内容项目下载完毕，共%s页" % page_num)
                break
            page_num += 1
            if page_num >= self.MAX_PAGE_NUM:
                break

    def inv_download_all(self, month, save_path, *args, **kwargs):
        page_num = 1

        while True:
            html = self.api_query_card(page_num, *args, **kwargs)
            if html is None:
                page_num += 1
                continue
            for cardid, car_num in self.__get_query_cardid(html):
                self.inv_download(cardid, month, car_num, save_path)
            if not self.__has_next_page(etree.HTML(html)):
                break
            page_num += 1
            if page_num >= self.MAX_PAGE_NUM:
                break

    def set_max_page_num(self, max_page_num):
        self.MAX_PAGE_NUM = max_page_num

    def __create_filename(self, invinfo, car_num, extention="zip"):
        datetime_ = datetime.datetime.strptime(
            invinfo["datetime"], "%Y-%m-%d %H:%M:%S")
        template = "%(car_num)s_%(datetime)s_金额%(amount)s_数量%(count)s_%(type)s.%(ext)s"
        filename = template % {
            "car_num": car_num,
            "datetime": datetime_.strftime("%Y%m%d_%H%M"),
            "amount": invinfo["amount"],
            "count": invinfo["count"],
            "type": invinfo["type"],
            "ext": extention,
        }
        return filename

    def __parse_query_apply(self, html):
        inv_info = []
        xphtml = etree.HTML(html)
        invs = xphtml.xpath("//table[@class='table_wdfp']")
        if invs:
            for inv in invs:
                temp = {
                    "datetime": inv.xpath("./tr[1]/td/table/tr[1]/th[1]/text()")[0][7:],
                    "type": inv.xpath("./tr[1]/td/table/tr[1]/th[3]/text()")[0],
                    "count": inv.xpath("./tr[2]/td/table/tr/td[3]/span/text()")[0],
                    "amount": re.match(
                        "[^\d\.]*([\d\.]*)",
                        inv.xpath("./tr[1]/td/table/tr[1]/th[2]/span/text()")[0]).groups()[0],
                    "dwurl": os.path.join(
                        "https://pss.txffp.com/",
                        inv.xpath(
                            "./tr[1]/td/table/tr/th[4]/a[2]")[0].get("href")[1:],
                    ),
                }
                inv_info.append(temp)
                self.logger.info("获得发票目标数据: %s" % str(temp))
        return inv_info

    def __get_query_cardid(self, html):
        xphtml = etree.HTML(html)
        cardid_list = []
        cards = xphtml.xpath("//dl[@class='etc_card_dl']/div/a")
        if not cards:
            return cardid_list

        for card in cards:
            id = card.get("href")[40:-8]
            car_num = card.xpath("./dd[2]/text()")[0].strip()[-7:]
            cardid_list.append((id, car_num))
            self.logger.info("获得[%s]对应id: %s" % (car_num, id))
        return cardid_list

    def __get_cardid(self, html):
        """返回嵌套id和车牌号元祖的列表"""
        xphtml = etree.HTML(html)
        cardid_list = []
        cards = xphtml.xpath("//dl[@class='etc_card_dl']/div/a")
        if not cards:
            return cardid_list
        for card in cards:
            id = re.match(r"[^(]*\('([\w]*)'\)", card.get("onclick")).groups()[0]
            car_num = re.match(
                "[^:]*：(.*)", card.xpath("dd[2]/text()")[0]).groups()
            # print(id, car_num)
            cardid_list.append((id, car_num))
            logging.info("获得车牌号[%s]的id: %s" % (car_num, id))
        return cardid_list

    def __get_applyid(self, html):
        """返回(apply_id, id, user_type)"""
        xphtml = etree.HTML(html)
        apply_id = xphtml.xpath("//form[@id='checkForm']/input[@id='applyId']")
        id = xphtml.xpath("//form[@id='checkForm']/input[@id='id']")
        user_type = xphtml.xpath(
            "//form[@id='checkForm']/input[@id='userType']")
        tmp = [apply_id, id, user_type]
        for n, i in enumerate(tmp):
            if i:
                tmp[n] = i[0].get("value")
            else:
                tmp[n] = ""
        self.logger.info("获得applyId: [%s], id: [%s], user_type: [%s]" %
                     (tmp[0], tmp[1], tmp[2]))
        return tmp

    def __get_tradeid(self, xphtml):
        """返回tradeid列表信息"""
        tradeid_list = []
        results = xphtml.xpath(
            '//tr/td[@class="tab_tr_td10"]/input[@class="check_one"]')
        if results:
            for res in results:
                id = res.get("value")
                if not id: continue
                id = re.match(r"[^_]*", id).group()
                if not id: continue
                tradeid_list.append(id)
        self.logger.info("获得[%s]条tradeid信息" % len(tradeid_list))
        return tradeid_list

    def __has_next_page(self, xphtml):
        """判断是否存在下一页，返回True或者False"""
        has_more = xphtml.xpath('//label[@id="taiji_search_hasMore"]/text()')
        if has_more and has_more[0] == "true":
            return True
        else:
            return False


def run():
    description = "如果请求失败，请更新你的cookie信息。\r\n如果在网络请求中出现异常等程序中断，可等待网络恢复后重试。"
    parser = argparse.ArgumentParser(description=description)

    unique_opts = parser.add_mutually_exclusive_group(required=True)
    unique_opts.add_argument("-d", "--download", action="store_true", dest="download", help="下载发票文件，需要指定对象，以及月份和保存目录")
    unique_opts.add_argument("-i", "--invoicev", action="store_true", dest="invoice", help="开票，需要指定开票月和对象")

    unique_opts_ = parser.add_mutually_exclusive_group(required=False)
    unique_opts_.add_argument("-a", "--all", action="store_true", default=True, dest="all", help="执行全部")
    unique_opts_.add_argument("-c", "--cardid", action="store", dest="cardid", help="指定车辆编号，注意：cardid不是指车牌号（不推荐）")

    parser.add_argument("-e", "--email", action="store", dest="email", help="开票时的发票文件接收邮箱地址")
    parser.add_argument("-m", "--month", action="store", dest="month", help="目标年月份，例如2018年4月为：201804", required=True)
    parser.add_argument("-s", "--savedir", action="store", dest="savedir", help="发票文件保存路径")
    parser.add_argument("-w", "--waite", action="store_true", default=False, dest="waite", help="是否在每次进行网络请求间进行睡眠(默认睡眠1-3秒)，可减轻对方服务器鸭梨")

    options = parser.parse_args()

    def print_exit(text):
        print(text)
        sys.exit()

    # 验证月份的合法性
    if not re.match(r"^20[0-3]\d(0\d|1[0-2])$", options.month):
        print_exit("月份信息格式错误")

    event_handler = APIHandler(COOKIE, HEADERS, req_sleep=options.waite)
    # event_handler.set_max_page_num(12)

    # 下载
    if options.download:
        # 判断路径信息是否存在
        if not options.savedir:
            print_exit("你需要指定一个保存路径")
        else:
            if not os.path.isdir(options.savedir):
                print_exit("错误的目标路径")

        if options.all:
            event_handler.inv_download_all(options.month, options.savedir)
        elif options.cardid:
            event_handler.inv_download(options.cardid, options.month, options.save_path)
    # 开票
    elif options.invoice:
        if options.all:
            event_handler.submit_apply_all(options.month, options.email)
        elif options.cardid:
            event_handler.submit_apply(options.cardid, options.month, options.email)
            
    event_handler.logger.info("任务完成")


def main():
    run()

if __name__ == "__main__":
    main()
