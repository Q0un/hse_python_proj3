"""
Нагрузочное тестирование.

Запуск:
    locust -f locustfile.py --host http://localhost:8000

Затем откройте http://localhost:8089 и настройте количество пользователей.
"""

import random
import uuid

from locust import HttpUser, between, task


class ShortenerUser(HttpUser):
    wait_time = between(0.3, 1.5)
    BASE_URL = "https://ya.ru/load"

    def on_start(self):
        name = f"load_{uuid.uuid4().hex[:8]}"
        self.client.post(
            "/auth/signup", json={"login": name, "password": "pass"}
        )
        r = self.client.post(
            "/auth/login", json={"login": name, "password": "pass"}
        )
        self.token = r.json().get("access_token", "")
        self.headers = {"Authorization": f"Bearer {self.token}"}

        r = self.client.post(
            "/links/shorten",
            json={"url": self.BASE_URL},
            headers=self.headers,
        )
        code = r.json().get("code", "fallback")
        self.created_links = [{"code": code, "url": self.BASE_URL}]

    @task(5)
    def follow_link(self):
        link = random.choice(self.created_links)
        self.client.get(
            f"/links/{link['code']}",
            allow_redirects=False,
            name="/links/[code]",
        )

    @task(3)
    def create_link(self):
        url = f"https://ya.ru/{uuid.uuid4().hex[:6]}"
        r = self.client.post(
            "/links/shorten",
            json={"url": url},
            headers=self.headers,
        )
        code = r.json().get("code")
        if code:
            self.created_links.append({"code": code, "url": url})

    @task(2)
    def get_stats(self):
        link = random.choice(self.created_links)
        self.client.get(
            f"/links/{link['code']}/stats",
            name="/links/[code]/stats",
        )

    @task(1)
    def search_link(self):
        link = random.choice(self.created_links)
        self.client.get(
            "/links/search",
            params={"original_url": link["url"]},
            name="/links/search",
        )
