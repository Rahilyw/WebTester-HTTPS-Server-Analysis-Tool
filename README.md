# 🌐 WebTester

> A low-level HTTP/HTTPS diagnostic tool built entirely on raw sockets — no `requests`, no `urllib`, no shortcuts.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)
![Protocol](https://img.shields.io/badge/Protocol-HTTP%2F1.1-orange?style=flat-square)
![TLS](https://img.shields.io/badge/TLS-ALPN%20%2F%20HTTP2%20Detection-green?style=flat-square)
![Sockets](https://img.shields.io/badge/Networking-Raw%20Sockets-blueviolet?style=flat-square)

---

## What It Does

WebTester is a command-line tool that probes a web server and surfaces three key properties:

| # | Check | Details |
|---|-------|---------|
| 1 | **HTTP/2 Support** | Detects `h2` via TLS ALPN negotiation |
| 2 | **Cookie Inventory** | Name, expiry, and domain for every `Set-Cookie` header |
| 3 | **Password Protection** | Detects HTTP `401 Unauthorized` responses |

All redirect chains (301/302) are followed automatically until the final destination is reached.

---

## Why This Project Stands Out

Most networking assignments reach for `requests` or `http.client`. This one doesn't.

WebTester is implemented using **only Python's standard socket and SSL libraries** — meaning every byte of the HTTP request is hand-crafted, every response is parsed manually, and every redirect is resolved from scratch. This reflects a ground-up understanding of how the web actually works at the protocol level.

Key implementation decisions:

- **ALPN negotiation** — wraps the socket in a `ssl.SSLContext`, offers `['h2', 'http/1.1']`, and reads back the negotiated protocol to detect HTTP/2 support
- **Forced HTTP/1.1 fallback** — after detecting `h2`, reconnects via plain HTTP/1.1 to issue a human-readable GET request for cookie and auth analysis
- **Manual redirect resolution** — parses `Location` headers and reconstructs absolute URLs from relative paths across domain boundaries
- **Header-only cookie parsing** — extracts `Set-Cookie` fields without any cookie library; parses `name`, `expires`, and `domain` attributes by splitting raw header strings

---

## Sample Output

```
website: www.uvic.ca
1. Supports http2: No
2. List of Cookies:
cookie name: PHPSESSID
cookie name: uvic_bar, expires time: Thu, 01 Jan 1970 00:00:01 GMT; domain name: .uvic.ca
cookie name: www_def
cookie name: TS018b3cbd
cookie name: TS0165a077; domain name: .uvic.ca
3. Password-protected: No
```

---

## Usage

**Requires:** Python 3 on a Linux system (tested on `linux.csc.uvic.ca`)

```bash
# Pass the URL directly
python3 WebTester.py www.uvic.ca
python3 WebTester.py https://www.google.com

# Or run interactively
python3 WebTester.py
# → Please enter URL: _
```

No dependencies to install. No virtual environment needed.

---

## How It Works

```
User Input
    │
    ▼
Parse URL  ──────────────────────────────────────────────────────────────────────────
    │                                                                                │
    ▼                                                                             (HTTPS)
Open raw TCP socket                                                           Wrap in SSL
    │                                                                                │
    └──────────────────────────┬─────────────────────────────────────────────────────┘
                               │
                               ▼
                     ALPN negotiation
                    ┌─────────────────┐
                    │  h2 detected?   │
                    └────────┬────────┘
                      Yes    │    No
               ┌─────────────┘    └──────────────────┐
               ▼                                      ▼
    Log "Supports HTTP/2: Yes"          Issue HTTP/1.1 GET request
    Reconnect via HTTP/1.1              over existing connection
               │                                      │
               └──────────────┬───────────────────────┘
                              │
                              ▼
                     Read HTTP response
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         301/302          200 OK            401
         Redirect         Parse:          Password
         → follow         Cookies         Protected
                          headers
```

---

## Files

```
WebTester/
├── WebTester.py   # Core implementation (~all socket, SSL, and HTTP logic)
└── README.md      # This file
```

---

## Technical Concepts Demonstrated

- **Socket programming** — `socket.create_connection()`, manual send/recv loops
- **TLS/SSL in Python** — `ssl.SSLContext`, certificate verification, ALPN extension
- **HTTP/1.1 request formatting** — correct CRLF line endings, `Host` and `Connection` headers
- **HTTP response parsing** — status line extraction, header field splitting, chunked body handling
- **Redirect handling** — recursive resolution with absolute/relative URL reconstruction
- **Cookie header parsing** — raw string parsing of `Set-Cookie` directives without library support

---

## Context

Built as part of **CSc 361: Computer Communications and Networks** at the University of Victoria (Spring 2026). The constraint to use only raw sockets was intentional — the goal was understanding the protocol, not wrapping it.

---

*Rahil Wijeyesekera · University of Victoria · V01041863*
