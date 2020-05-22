import requests
from lxml import etree
import os
import time
import datetime
import re
from multiprocessing.dummy import Pool
import sys
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice, TagExtractor
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.cmapdb import CMapDB
from pdfminer.layout import LAParams
from pdfminer.image import ImageWriter
from concurrent.futures import ProcessPoolExecutor
import logging
import utils
import glob

log = logging.getLogger()
log.root.setLevel(logging.INFO)
# sh = logging.StreamHandler()
# log.addHandler(sh)

template_folder="/root/crawl/templates"

key_orgs = ["Google", "Facebook", "Hugging Face", "Deepmind", 
        "Microsoft","Alibaba", "Stanford", "Cambridge", "Oxford", "Harvard", 
        "Carnegie Mellon University", "Amazon", "Fudan", "Adobe", "Berkeley", 
        "Tencent", "Chinese Academy of Sciences", "Tsinghua", "Nvidia", "Intel ", 
        "UCL", "IBM"]

def main():
    generate_daily()

def generate_daily():
    date, terms = get_daily_papers()
    # insert to db
    log.info(f"add {len(terms)} papers to database")
    db = utils.Database(log)
    values = [(p.id, p.url, p.title, p.author, p.org, p.comment, p.subject) for p in terms]
    db.batch_update("arxiv", "paper_id", "paper_id,url,title,author,org,comment,subject",values)
    db.close()
    # create html
    columns = ["Title", "Org", "Comment", "Author"]
    arxiv_raw = os.path.join(template_folder, "arxiv_raw.html")
    arxiv_pc = os.path.join(template_folder, "arxiv.html")
    pc_head = os.path.join(template_folder, "template_head.html")
    pc_tail = os.path.join(template_folder, "template_tail.html")
    with open(arxiv_raw, "w") as fout:
        fout.write('<div class="container pb-3">\n')
        fout.write(f'<p><kbd>Arxiv NLP - {date}</kbd></p>\n')
        fout.write('<p><kbd>本服务由微信公众号「夕小瑶的卖萌屋」提供</kbd></p>\n')
        fout.write('</div>\n')
        fout.write('<table style="width: 100%">\n')
        fout.write('<colgroup>\n')
        fout.write('<col span="1" style="width: 35%;">\n')
        fout.write('<col span="1" style="width: 15%;">\n')
        fout.write('<col span="1" style="width: 25%;">\n')
        fout.write('<col span="1" style="width: 35%;">\n')
        fout.write('</colgroup>\n')
        fout.write('<thead><tr class="table100-head">\n')
        for idx, column_name in enumerate(columns):
            if column_name=="Title":
                fout.write(f'<th class="text-center">{column_name}</th>\n')
            else:
                fout.write(f'<th>{column_name}</th>\n')
        fout.write('</tr></thead><tbody>\n')
        for paper in terms:
            fout.write('<tr>\n')
            fout.write(f"<td class='column3'><a href='{paper.url}'>{paper.title}</a></td>\n")
            if len(paper.org)>0:
                fout.write(f"<td class='column3'>{paper.org}</td>\n")
            else:
                fout.write(f"<td class='column3'>-</td>\n")
            if len(paper.comment)>0:
                fout.write(f"<td class='column3'>{paper.comment}</td>\n")
            else:
                fout.write(f"<td class='column3'>-</td>\n")
            fout.write(f"<td class='column3'>{paper.author}</td>\n")
            fout.write('</tr>\n')
        fout.write('</table>\n')
    os.system(f"rm -rf {arxiv_pc}")
    os.system(f"cat {pc_head} {arxiv_raw} {pc_tail} >> {arxiv_pc}")


class Paper(object):
    def __init__(self, url, title, author, org, comment, subject):
        self.id = url.replace("/abs/","")
        self.url = "https://arxiv.org"+url
        self.title = title
        self.author = author
        self.org = org
        self.comment = comment
        self.subject = subject

def get_daily_papers():
    res = []
    #### remove caches ###
    pdf_folder = "/root/crawl/tmp_pdf"
    pdf_caches = glob.glob(f"{pdf_folder}/*")
    if len(pdf_caches)>=100:
        os.system(f"rm -rf {pdf_folder}/*")
    #### main ###
    url0 = 'http://arxiv.org/list/cs.CV/recent'
    url0 = 'https://arxiv.org/list/cs.CL/pastweek?show=99'
    log.info(url0)
    # xpath of each page
    date_id = 1
    link_path = f'//dl[{date_id}]//*[@class="list-identifier"]//a[1]//@href'  # pdf href list
    xp_date = f'//*[@id="dlpage"]/h3[{date_id}]/text()'  # date->folder

    htm0 = getHtml(url0)
    links = getContent(htm0, link_path)  # get pdfs' href
    cons_date = getContent(htm0, xp_date) # get date
    folder = cons_date[0].split(', ') # get date string

    log.info(folder[1] + ': having %s' % len(links) + ' files')
    #### download ###
    log.info("downloading..")
    start = datetime.datetime.now()
    inputs = [('https://arxiv.org/pdf' + x.replace("abs/","") + ".pdf", x.replace("abs","").replace("/",""), pdf_folder) for x in links]
    pdf_names = []
    try:
        executor = ProcessPoolExecutor(max_workers=10)
        pdf_names = executor.map(getDownPdf, inputs)
        executor.shutdown(wait=True)
    except Exception as e:
        log.error(e)
    pdf_names = list(pdf_names)
    end = datetime.datetime.now()
    log.info(f"finished downloading, cost: {(end-start).seconds / 60} mins")
    for i in range(len(links)):
        try:
            title_path = f'//dl[1]//dd[{i+1}]//*[@class="list-title mathjax"]/text()' 
            author_path = f'//dl[1]//dd[{i+1}]//*[@class="list-authors"]//a/text()'  
            comment_path = f'//dl[1]//dd[{i+1}]//*[@class="list-comments mathjax"]/text()' 
            pri_subject_path = f'//dl[1]//dd[{i+1}]//*[@class="primary-subject"]/text()' 
            subject_path = f'//dl[1]//dd[{i+1}]//*[@class="list-subjects"]/text()' 
            title = getContent(htm0, title_path) 
            title = [x.strip() for x in title if len(x.strip())>0]
            if len(title)>0:
                title = title[0]
            else:
                continue
            author = getContent(htm0, author_path)
            author_str = ", ".join(author)
            comment = getContent(htm0, comment_path)
            comment = [x.strip() for x in comment if len(x.strip())>0]
            if len(comment)>0 and "admin note" not in comment[0]:
                comment = comment[0]
            else:
                comment = ""
            pri_subject = getContent(htm0, pri_subject_path)[0]
            subject = getContent(htm0, subject_path)
            subject = [x.strip() for x in subject if len(x.strip())>0]
            if len(subject)>0:
                subject = pri_subject+subject[0]
            else:
                subject = pri_subject
            orig_infos = []
            if len(pdf_names)>0 and len(pdf_names[i])>0:
                orig_infos = get_org_info(pdf_names[i], title, author)
            orig_infos_str = "; ".join(orig_infos).strip().lower()
            orgs = [x for x in key_orgs if orig_infos_str.find(x.lower())>-1]
            key_org_info = ','.join(orgs)
            res.append(Paper(links[i], title, author_str, key_org_info, comment, subject))
            # exit()
        except Exception as e:
            log.error(e)
            continue
    return folder[1], res

def getHtml(url):
    html = requests.get(url).content
    selector = etree.HTML(html)
    return selector

def getContent(htm, xpathStr):
    selector = htm
    content = selector.xpath(xpathStr)  
    return content

def getDownPdf(inputs):
    url, title, folder = inputs
    try:
        fl = os.path.join(folder, title+".pdf")
        if os.path.exists(fl):
            return fl
        r = requests.get(url)
        with open(fl, "wb") as code:
            code.write(r.content)
        # log.info(f"finish {title}")
        return fl
    except Exception as e:
        return ""

def get_org_info(filename, title, authors):
    os.system("pdf2txt.py -o tmp.txt -t text -p 1 "+filename.replace(" ", "\ "))
    title_set = set([x.strip().lower() for x in title.split()])
    authors_set = set()
    for a in authors:
        for x in a.split():
            authors_set.add(x.strip().lower())
    email_pat = re.compile(r"@([\w-]+\.)+[a-z]{2,3}")
    digit_pat = re.compile(r"[0-9]|‡|#|;|¨|♦|∗")
    org_infos = []
    find_title = False
    with open("tmp.txt") as fin:
        for line in fin:
            line = line.strip()
            if re.search(email_pat, line, flags=0) is not None:
                break
            if line.lower().find("abstract")>-1 or line.lower().find("introduction")>-1 :
                break
            line = re.sub(digit_pat, "", line).strip()
            if len(line)<=1: continue
            lst = set([x.strip().lower() for x in line.split()])
            if len(lst & title_set)>0:
                find_title=True
                continue
            if not find_title:
                continue
            if len(lst & authors_set)>0:
                continue
            if line.find("/")>-1: continue
            if line.find("@")>-1: continue
            # if len(line)<4: continue
            # if len(line)>50: continue
            # if line.find(",")>-1: continue
            if line not in org_infos:
                org_infos.append(line)
    return org_infos

if __name__ == "__main__":
    log_file_handler = utils.get_log_handler("/root/crawl/log.arxiv/")
    log.addHandler(log_file_handler)
    main()
    log.removeHandler(log_file_handler)