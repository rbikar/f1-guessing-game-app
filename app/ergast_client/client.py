import logging
import os
import threading

import requests
from more_executors import Executors
from time import sleep

LOG = logging.getLogger(__name__)

API = "api/f1"


REQUESTS_MAX_WORKERS = int(os.getenv("F1_ERGAST_REQUESTS_MAX_WORKERS", "4"))
SLEEP_SECONDS = 2


class Client(object):
    def __init__(self, url):
        self._url = os.path.join(url, API)
        self._tls = threading.local()
        self._executor = (
            Executors.thread_pool(max_workers=REQUESTS_MAX_WORKERS)
            .with_map(self._unpack_response)
            .with_retry()
        )

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self._executor.__exit__(*args, **kwargs)

    def _unpack_response(self, response):
        try:
            out = response.json()
        except Exception:
            response.raise_for_status()
            raise

        response.raise_for_status()
        return out

    @property
    def _session(self):
        if not hasattr(self._tls, "session"):
            self._tls.session = requests.Session()
        return self._tls.session

    def _do_request(self, **kwargs):
        # due to ergast API limitations we need to wait between requests in order not to exceed limits
        LOG.debug("Waiting %s seconds before making request", SLEEP_SECONDS)
        sleep(SLEEP_SECONDS)
        return self._session.request(**kwargs)

    def get_current_schedule(self):
        # https://ergast.com/api/f1/2024.json
        endpoint = "2024"
        url = os.path.join(self._url, endpoint + ".json")
        LOG.debug("Getting all races for season %s", endpoint)
        return self._executor.submit(self._do_request, method="GET", url=url)

    def get_result(self, round, rank):
        endpoint = f"2024/{round}/results/{rank}.json"
        url = os.path.join(self._url, endpoint)
        LOG.debug("Getting result for race, round %s: %s", round, endpoint)

        return self._executor.submit(self._do_request, method="GET", url=url)

    def get_q_result(self, round, rank):
        endpoint = f"2024/{round}/qualifying/{rank}.json"
        url = os.path.join(self._url, endpoint)
        LOG.debug("Getting result for Q, rank: %s, round %s: %s", round, rank, endpoint)
        return self._executor.submit(self._do_request, method="GET", url=url)

    def get_sprint_result(self, round, rank):
        endpoint = f"2024/{round}/sprint/{rank}.json"
        url = os.path.join(self._url, endpoint)
        LOG.debug(
            "Getting result for sprint, rank: %s, round %s: %s", round, rank, endpoint
        )

        return self._executor.submit(self._do_request, method="GET", url=url)

    def get_fastest_lap(self, round, rank):
        endpoint = f"2024/{round}/fastest/{rank}/results.json"
        url = os.path.join(self._url, endpoint)
        LOG.debug(
            "Getting result of fastest lap, rank: %s, round %s: %s",
            round,
            rank,
            endpoint,
        )

        return self._executor.submit(self._do_request, method="GET", url=url)
