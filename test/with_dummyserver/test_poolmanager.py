import unittest
import json

import pytest

from dummyserver.server import HAS_IPV6
from dummyserver.testcase import HTTPDummyServerTestCase, IPv6HTTPDummyServerTestCase
from urllib3.poolmanager import PoolManager
from urllib3.connectionpool import port_by_scheme
from urllib3.exceptions import MaxRetryError
from urllib3.util.retry import Retry


class TestPoolManager(HTTPDummyServerTestCase):
    def setUp(self):
        self.base_url = "http://%s:%d" % (self.host, self.port)
        self.base_url_alt = "http://%s:%d" % (self.host_alt, self.port)

    def test_redirect(self):
        with PoolManager() as http:
            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/" % self.base_url},
                redirect=False,
            )

            assert r.status == 303

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/" % self.base_url},
            )

            assert r.status == 200
            assert r.data == b"Dummy server!"

    def test_redirect_twice(self):
        with PoolManager() as http:

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/redirect" % self.base_url},
                redirect=False,
            )

            assert r.status == 303

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={
                    "target": "%s/redirect?target=%s/" % (self.base_url, self.base_url)
                },
            )

            assert r.status == 200
            assert r.data == b"Dummy server!"

    def test_redirect_to_relative_url(self):
        with PoolManager() as http:

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "/redirect"},
                redirect=False,
            )

            assert r.status == 303

            r = http.request(
                "GET", "%s/redirect" % self.base_url, fields={"target": "/redirect"}
            )

            assert r.status == 200
            assert r.data == b"Dummy server!"

    def test_cross_host_redirect(self):
        with PoolManager() as http:

            cross_host_location = "%s/echo?a=b" % self.base_url_alt
            try:
                http.request(
                    "GET",
                    "%s/redirect" % self.base_url,
                    fields={"target": cross_host_location},
                    timeout=1,
                    retries=0,
                )
                self.fail(
                    "Request succeeded instead of raising an exception like it should."
                )

            except MaxRetryError:
                pass

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/echo?a=b" % self.base_url_alt},
                timeout=1,
                retries=1,
            )

            assert r._pool.host == self.host_alt

    def test_too_many_redirects(self):
        with PoolManager() as http:

            try:
                r = http.request(
                    "GET",
                    "%s/redirect" % self.base_url,
                    fields={
                        "target": "%s/redirect?target=%s/"
                        % (self.base_url, self.base_url)
                    },
                    retries=1,
                )
                self.fail(
                    "Failed to raise MaxRetryError exception, returned %r" % r.status
                )
            except MaxRetryError:
                pass

            try:
                r = http.request(
                    "GET",
                    "%s/redirect" % self.base_url,
                    fields={
                        "target": "%s/redirect?target=%s/"
                        % (self.base_url, self.base_url)
                    },
                    retries=Retry(total=None, redirect=1),
                )
                self.fail(
                    "Failed to raise MaxRetryError exception, returned %r" % r.status
                )
            except MaxRetryError:
                pass

    def test_redirect_cross_host_remove_headers(self):
        with PoolManager() as http:

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/headers" % self.base_url_alt},
                headers={"Authorization": "foo"},
            )

            assert r.status == 200

            data = json.loads(r.data.decode("utf-8"))

            assert "Authorization" not in data

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/headers" % self.base_url_alt},
                headers={"authorization": "foo"},
            )

            assert r.status == 200

            data = json.loads(r.data.decode("utf-8"))

            assert "authorization" not in data
            assert "Authorization" not in data

    def test_redirect_cross_host_no_remove_headers(self):
        with PoolManager() as http:

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/headers" % self.base_url_alt},
                headers={"Authorization": "foo"},
                retries=Retry(remove_headers_on_redirect=[]),
            )

            assert r.status == 200

            data = json.loads(r.data.decode("utf-8"))

            assert data["Authorization"] == "foo"

    def test_redirect_cross_host_set_removed_headers(self):
        with PoolManager() as http:

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/headers" % self.base_url_alt},
                headers={"X-API-Secret": "foo", "Authorization": "bar"},
                retries=Retry(remove_headers_on_redirect=["X-API-Secret"]),
            )

            assert r.status == 200

            data = json.loads(r.data.decode("utf-8"))

            assert "X-API-Secret" not in data
            assert data["Authorization"] == "bar"

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={"target": "%s/headers" % self.base_url_alt},
                headers={"x-api-secret": "foo", "authorization": "bar"},
                retries=Retry(remove_headers_on_redirect=["X-API-Secret"]),
            )

            assert r.status == 200

            data = json.loads(r.data.decode("utf-8"))

            assert "x-api-secret" not in data
            assert "X-API-Secret" not in data
            assert data["Authorization"] == "bar"

    def test_raise_on_redirect(self):
        with PoolManager() as http:

            r = http.request(
                "GET",
                "%s/redirect" % self.base_url,
                fields={
                    "target": "%s/redirect?target=%s/" % (self.base_url, self.base_url)
                },
                retries=Retry(total=None, redirect=1, raise_on_redirect=False),
            )

            assert r.status == 303

    def test_raise_on_status(self):
        with PoolManager() as http:

            try:
                # the default is to raise
                r = http.request(
                    "GET",
                    "%s/status" % self.base_url,
                    fields={"status": "500 Internal Server Error"},
                    retries=Retry(total=1, status_forcelist=range(500, 600)),
                )
                self.fail(
                    "Failed to raise MaxRetryError exception, returned %r" % r.status
                )
            except MaxRetryError:
                pass

            try:
                # raise explicitly
                r = http.request(
                    "GET",
                    "%s/status" % self.base_url,
                    fields={"status": "500 Internal Server Error"},
                    retries=Retry(
                        total=1, status_forcelist=range(500, 600), raise_on_status=True
                    ),
                )
                self.fail(
                    "Failed to raise MaxRetryError exception, returned %r" % r.status
                )
            except MaxRetryError:
                pass

            # don't raise
            r = http.request(
                "GET",
                "%s/status" % self.base_url,
                fields={"status": "500 Internal Server Error"},
                retries=Retry(
                    total=1, status_forcelist=range(500, 600), raise_on_status=False
                ),
            )

            assert r.status == 500

    def test_missing_port(self):
        # Can a URL that lacks an explicit port like ':80' succeed, or
        # will all such URLs fail with an error?

        with PoolManager() as http:

            # By globally adjusting `port_by_scheme` we pretend for a moment
            # that HTTP's default port is not 80, but is the port at which
            # our test server happens to be listening.
            port_by_scheme["http"] = self.port
            try:
                r = http.request("GET", "http://%s/" % self.host, retries=0)
            finally:
                port_by_scheme["http"] = 80

            assert r.status == 200
            assert r.data == b"Dummy server!"

    def test_headers(self):
        with PoolManager(headers={"Foo": "bar"}) as http:

            r = http.request("GET", "%s/headers" % self.base_url)
            returned_headers = json.loads(r.data.decode())
            assert returned_headers.get("Foo") == "bar"

            r = http.request("POST", "%s/headers" % self.base_url)
            returned_headers = json.loads(r.data.decode())
            assert returned_headers.get("Foo") == "bar"

            r = http.request_encode_url("GET", "%s/headers" % self.base_url)
            returned_headers = json.loads(r.data.decode())
            assert returned_headers.get("Foo") == "bar"

            r = http.request_encode_body("POST", "%s/headers" % self.base_url)
            returned_headers = json.loads(r.data.decode())
            assert returned_headers.get("Foo") == "bar"

            r = http.request_encode_url(
                "GET", "%s/headers" % self.base_url, headers={"Baz": "quux"}
            )
            returned_headers = json.loads(r.data.decode())
            assert returned_headers.get("Foo") is None
            assert returned_headers.get("Baz") == "quux"

            r = http.request_encode_body(
                "GET", "%s/headers" % self.base_url, headers={"Baz": "quux"}
            )
            returned_headers = json.loads(r.data.decode())
            assert returned_headers.get("Foo") is None
            assert returned_headers.get("Baz") == "quux"

    def test_http_with_ssl_keywords(self):
        with PoolManager(ca_certs="REQUIRED") as http:

            r = http.request("GET", "http://%s:%s/" % (self.host, self.port))
            assert r.status == 200

    def test_http_with_ca_cert_dir(self):
        with PoolManager(ca_certs="REQUIRED", ca_cert_dir="/nosuchdir") as http:

            r = http.request("GET", "http://%s:%s/" % (self.host, self.port))
            assert r.status == 200


@pytest.mark.skipif(not HAS_IPV6, reason="IPv6 is not supported on this system")
class TestIPv6PoolManager(IPv6HTTPDummyServerTestCase):
    def setUp(self):
        self.base_url = "http://[%s]:%d" % (self.host, self.port)

    def test_ipv6(self):
        with PoolManager() as http:
            http.request("GET", self.base_url)


if __name__ == "__main__":
    unittest.main()
