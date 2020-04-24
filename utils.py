import requests as r
from bs4 import BeautifulSoup
import pandas as pd
import csv
import threading
import time
import requests
from lxml import etree
import logging
from logging.handlers import TimedRotatingFileHandler
from logging.handlers import RotatingFileHandler
import pymysql
import os
import re

class Database(object):
    # https://blog.csdn.net/zhihua_w/article/details/54313258
    def __init__(self, logger):
        # 打开数据库连接（ip/数据库用户名/登录密码/数据库名）
        self.db = pymysql.connect("localhost", "root", "0000000", "00000")
        # 使用 cursor() 方法创建一个游标对象 cursor
        self.cursor = self.db.cursor()
        self.logger = logger

    def get_latest(self, table_name, k=100):
        # SQL 查询语句
        sql = f"SELECT * FROM {table_name} ORDER BY created DESC LIMIT {k}"
        try:
            # 执行SQL语句
            self.cursor.execute(sql)
            # 获取所有记录列表
            results = self.cursor.fetchall()
            return results
        except Exception as e:
            self.logger.error(e)
        return []

    def batch_update(self, table_name, primary_key, fields, values):
        for val in values:
            # insert
            val = [x.replace(",",";") for x in val]
            # value_str = "'"+"','".join(val)+"'"
            value_str = '"'+'","'.join(val)+'"'
            try:
                sql = f"DELETE FROM {table_name} WHERE {primary_key} = {val[0]}"
                self.cursor.execute(sql)
                sql = f"INSERT INTO {table_name} ({fields}) VALUES ({value_str});"
                self.cursor.execute(sql)
                # 提交到数据库执行
                self.db.commit()
            except Exception as e:
                # 如果发生错误则回滚
                self.db.rollback()
                self.logger.error(e)
                self.logger.error(sql)
                continue

    def write_to_csv(self, table_name, filename, column_names, k=100):
        if os.path.exists(filename):
            os.remove(filename)
        rows = self.get_latest(table_name, k)
        with open(filename, "w", encoding="GB18030") as fout:
            fout.write(column_names+"\n")
            for val in rows:
                fout.write(",".join([str(x) for x in val])+"\n")
        return len(rows)

    def write_to_html(self, table_name, out_file, column_names, k=100):
        if os.path.exists(out_file):
            os.remove(out_file)
        name2id, id2name = {}, {}
        for idx, name in enumerate(column_names):
            name2id[name] = idx
            id2name[idx] = name
        rows = self.get_latest(table_name, k)
        with open(out_file, "w") as fout:
            fout.write('<html>\n<body>\n<table border="1">\n')
            fout.write('<tr>\n')
            for name in column_names:
                if name in ["id", "url"]: continue
                fout.write(f'<th>{name}</th>\n')
            fout.write('</tr>\n')
            for data_row in rows:
                fout.write('<tr>\n')
                url = data_row[name2id['url']]
                for idx, val in enumerate(data_row):
                    if id2name[idx] in ["id", "url"]: continue
                    if id2name[idx] == "title": 
                        fout.write(f"<td><a href='{url}'>{val}</a></td>\n")
                    else:
                        fout.write(f"<td>{val}</td>\n")
                fout.write('</tr>\n')
            fout.write('</table>\n</body>\n</html>\n')
        return len(rows)

    def close(self):
        self.db.close()
    
def demoji(text):
	emoji_pattern = re.compile("["
		u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U00010000-\U0010ffff"
	                           "]+", flags=re.UNICODE)
	return(emoji_pattern.sub(r'', text))

def get_log_handler(log_path):
    LOG_PATH = log_path
    log_fmt = '[%(asctime)s - File \"%(filename)s\",line %(lineno)s - %(levelname)s]: %(message)s'
    formatter = logging.Formatter(log_fmt)
    log_file_handler = TimedRotatingFileHandler(filename=LOG_PATH+"log", when="D", interval=1, backupCount=30)
    # log_file_handler = TimedRotatingFileHandler(filename=LOG_PATH+"log", when="H", interval=4, backupCount=30)
    # log_file_handler.suffix = "%Y-%m-%d_%H-%M-%S.log"
    # log_file_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}.log$")
    log_file_handler.setFormatter(formatter)
    return log_file_handler

def getContent(htm, xpathStr):
    selector = htm
    content = selector.xpath(xpathStr)  
    return content

if __name__ == '__main__':
    csr = connect_db()

    pass
