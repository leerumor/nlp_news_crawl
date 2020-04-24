python server_arxiv.py \
    --port=8001 \
    --log_file_prefix=/root/crawl/log.arxiv_server/log \
    --log_rotate_mode=time \
    --log_rotate_when=D \
    --log_rotate_interval=1

# define("log_file_prefix", default="/root/crawl/log.arxiv_server/log")
# define("log_rotate_mode", default='time')   # 轮询模式: time or size
# define("log_rotate_when", default='D')      # 单位: S / M / H / D / W0 - W6
# define("log_rotate_interval", default=1)   # 间隔: 60秒