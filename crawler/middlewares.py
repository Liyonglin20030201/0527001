from fake_useragent import UserAgent


class RandomUserAgentMiddleware:
    """随机User-Agent中间件，降低被反爬检测的风险"""

    def __init__(self):
        self.ua = UserAgent()

    def process_request(self, request, spider):
        request.headers["User-Agent"] = self.ua.random
