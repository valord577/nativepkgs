#!/usr/bin/env python3

import hmac
import http.client
import os
import sys
import time
from hashlib import sha256
from typing import Any, Callable, NoReturn
from urllib.parse import quote as escape

sign_expires_in_seconds = "60"
environ_key_http_debug = "HTTP_DEBUG_MESSAGE"
oss_storage_basedir = os.getenv("GH_OSSUTIL_PKGS")

_ak = os.getenv("GH_OSSUTIL_AK")
_sk = os.getenv("GH_OSSUTIL_SK")
_cdn = os.getenv("GH_OSSUTIL_CNAME")
_bucket = os.getenv("GH_OSSUTIL_BUCKET")
_region = os.getenv("GH_OSSUTIL_REGION")


def tls() -> bool:
    tls = True
    if tls:
        try:
            import ssl  # noqa: F401
        except ImportError:
            tls = False
    return tls


def sign(
    method: str,
    oss_path: str,
    ak: str,
    sk: str,
    bucket: str,
    region: str,
    headers: dict[str, str] = {},
    queries: dict[str, str] = {},
) -> dict[str, str]:
    iso8601 = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    # iso8601 = "20231203T121212Z"
    iso8601_date = iso8601[:8]
    _queries = {
        **queries,
        **{
            "x-oss-signature-version": "OSS4-HMAC-SHA256",
            "x-oss-credential": f"{ak}/{iso8601_date}/{region}/oss/aliyun_v4_request",
            "x-oss-date": iso8601,
            "x-oss-expires": sign_expires_in_seconds,
        },
    }
    sorted_keys = sorted(_queries.keys())

    canonical_queries = ""
    for key in sorted_keys:
        canonical_queries += f"{escape(key, safe='')}={escape(_queries[key], safe='')}&"
    canonical_queries = canonical_queries[: len(canonical_queries) - 1]

    _headers: dict[str, str] = {}  # key.lower() -> value
    for key in headers.keys():
        k = key.lower()
        if (k == "content-type") or (k == "content-md5") or (k.startswith("x-oss-")):
            _headers[k] = headers[key]
    sorted_keys = sorted(_headers.keys())

    canonical_headers = ""
    for key in sorted_keys:
        canonical_headers += f"{key}:{_headers[key].strip()}\n"

    canonical_request = f"{method.upper()}\n/{bucket}/{escape(oss_path)}\n{canonical_queries}\n{canonical_headers}\n\nUNSIGNED-PAYLOAD".encode()
    # canonical_request = (
    #     "PUT\n"
    #     + "/examplebucket/exampleobject\n"
    #     + "x-oss-additional-headers=host&x-oss-credential=accesskeyid%2F20231203%2Fcn-hangzhou%2Foss%2Faliyun_v4_request&x-oss-date=20231203T121212Z&x-oss-expires=86400&x-oss-signature-version=OSS4-HMAC-SHA256\n"
    #     + "host:examplebucket.oss-cn-hangzhou.aliyuncs.com\n"
    #     + "x-oss-meta-author:alice\n"
    #     + "x-oss-meta-magic:abracadabra\n"
    #     + "\n"
    #     + "host\n"
    #     + "UNSIGNED-PAYLOAD"
    # ).encode()
    string_to_sign = f"OSS4-HMAC-SHA256\n{iso8601}\n{iso8601_date}/{region}/oss/aliyun_v4_request\n{sha256(canonical_request).hexdigest()}"

    h0 = hmac.new(f"aliyun_v4{sk}".encode(), iso8601_date.encode(), sha256)
    h1 = hmac.new(h0.digest(), region.encode(), sha256)
    h2 = hmac.new(h1.digest(), b"oss", sha256)
    h3 = hmac.new(h2.digest(), b"aliyun_v4_request", sha256)
    signature = hmac.new(h3.digest(), string_to_sign.encode(), sha256).hexdigest()
    # print(f"signature: {signature}") # 2c6c9f10d8950fb150290ef6f42570e33cd45d6a57ec7887de75fa2ec45b4c72
    return {**_queries, "x-oss-signature": signature}


def call(
    method: str,
    oss_path: str,
    body: Any,
    ak: str,
    sk: str,
    bucket: str,
    region: str,
    cdn: str = None,
    callback: Callable[[http.client.HTTPResponse], None] = None,
    headers: dict[str, str] = {},
    queries: dict[str, str] = {},
) -> None:
    _queries = sign(method, oss_path, ak, sk, bucket, region, headers, queries)
    url = f"/{oss_path}?"
    for k, v in _queries.items():
        url += f"{escape(k, safe='')}={escape(v, safe='')}&"
    url = url[: len(url) - 1]

    oss_host = cdn or f"{bucket}.oss-{region}.aliyuncs.com"
    if tls():
        conn = http.client.HTTPSConnection(oss_host)
    else:
        conn = http.client.HTTPConnection(oss_host)

    if os.environ.get(environ_key_http_debug):
        conn.set_debuglevel(1)
    conn.request(method, url, body, headers)
    resp = conn.getresponse()
    if callback:
        callback(resp)
    resp.close()
    conn.close()


def put_object(
    src: str, dst: str, ak: str, sk: str, bucket: str, region: str
) -> NoReturn:
    def callback(resp: http.client.HTTPResponse) -> None:
        if resp.getcode() != 200 and resp.getcode() != 204:
            print(f"respcode: {resp.getcode()}, respbody: ->\n{resp.read().decode()}")

    headers = {
        "x-oss-object-acl": "private",
        "Cache-Control": "public, max-age=7200",
        "Content-Disposition": "attachment",
        "Content-Type": "application/octet-stream",
    }
    with open(src, "rb") as f:
        _dst = dst.lstrip("/")
        if oss_storage_basedir:
            _dst = f"{oss_storage_basedir}/{_dst}".lstrip("/")
        call("PUT", _dst, f, ak, sk, bucket, region, callback=callback, headers=headers)


def get_object(
    src: str, dst: str, ak: str, sk: str, bucket: str, region: str, cdn: str = None
) -> NoReturn:
    def callback(resp: http.client.HTTPResponse) -> None:
        if resp.getcode() != 200 and resp.getcode() != 204:
            print(f"respcode: {resp.getcode()}, respbody: ->\n{resp.read().decode()}")
            return
        with open(dst, "wb") as f:
            while True:
                data = resp.read(8 * 1024)
                if not data:
                    break
                f.write(data)

    _src = src.lstrip("/")
    if oss_storage_basedir:
        _src = f"{oss_storage_basedir}/{_src}".lstrip("/")
    call("GET", _src, None, ak, sk, bucket, region, cdn=cdn, callback=callback)


if __name__ == "__main__":
    show_help = True
    if len(sys.argv) == 4 or len(sys.argv) == 5:
        offset = 1
        if len(sys.argv) == 5:
            offset = 2
            if sys.argv[1] == "-v":
                os.environ.setdefault(environ_key_http_debug, "1")

        args = sys.argv[offset:]
        if False:
            pass

        elif args[0] == "push":
            show_help = False
            put_object(args[1], args[2], _ak, _sk, _bucket, _region)
        elif args[0] == "pull":
            show_help = False
            get_object(args[1], args[2], _ak, _sk, _bucket, _region, _cdn)

    if show_help:
        print(f"Usage: {sys.argv[0]} [-v] <push|pull> <src> <dst>")
        sys.exit(1)
