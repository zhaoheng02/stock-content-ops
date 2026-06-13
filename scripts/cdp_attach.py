"""Attach to an existing Chrome tab (by URL substring) over CDP and run actions.

Usage:
    python3 scripts/cdp_attach.py "<url-substring>" <action> [args...]

Actions:
    info                      print current url + title
    shot <path>               screenshot
    text [selector]           innerText of selector (default body)
    click <selector>
    type <selector> <value>
    nav <url>                 navigate this tab
    eval <js>                 evaluate JS, print value
    waitfor <selector>        wait for selector
"""
import json
import sys
import urllib.request

sys.path.insert(0, "/Users/bytedance/X")
from cdp import _WS, CDP_HOST, CDP_PORT  # noqa: E402


def _tabs():
    url = "http://%s:%d/json" % (CDP_HOST, CDP_PORT)
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode())


def attach(substr):
    for t in _tabs():
        if t.get("type") != "page":
            continue
        if substr in (t.get("url") or "") or substr in (t.get("title") or ""):
            return t
    raise SystemExit("no tab matching: %s" % substr)


class Tab:
    def __init__(self, ws_url):
        self.ws = _WS(ws_url)
        self._id = 0
        self.send("Page.enable")
        self.send("Runtime.enable")
        self.send("DOM.enable")

    def send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s -> %s" % (method, msg["error"]))
                return msg.get("result", {})

    def eval(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", expression=expr,
                      returnByValue=True, awaitPromise=await_promise)
        if "exceptionDetails" in r:
            raise RuntimeError("JS error: %s" % json.dumps(r["exceptionDetails"]))
        return r.get("result", {}).get("value")

    def screenshot(self, path):
        import base64
        r = self.send("Page.captureScreenshot")
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return path


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    substr, action = sys.argv[1], sys.argv[2]
    rest = sys.argv[3:]
    info = attach(substr)
    tab = Tab(info["webSocketDebuggerUrl"])
    if action == "info":
        print(tab.eval("location.href"))
        print(tab.eval("document.title"))
    elif action == "shot":
        print(tab.screenshot(rest[0]))
    elif action == "text":
        sel = rest[0] if rest else "body"
        print(tab.eval("(document.querySelector(%s)||{}).innerText||''" % json.dumps(sel)))
    elif action == "click":
        ok = tab.eval("(function(){var e=document.querySelector(%s);if(!e)return false;e.click();return true;})()" % json.dumps(rest[0]))
        print("clicked" if ok else "NOT_FOUND")
    elif action == "type":
        sel, val = json.dumps(rest[0]), json.dumps(rest[1])
        ok = tab.eval("(function(){var e=document.querySelector(%s);if(!e)return false;e.focus();var d=Object.getOwnPropertyDescriptor(e.__proto__,'value');if(d&&d.set){d.set.call(e,%s);}else{e.value=%s;}e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));return true;})()" % (sel, val, val))
        print("typed" if ok else "NOT_FOUND")
    elif action == "nav":
        tab.send("Page.navigate", url=rest[0])
        print("navigating", rest[0])
    elif action == "eval":
        print(tab.eval(rest[0], await_promise=True))
    elif action == "waitfor":
        import time
        end = time.time() + 15
        while time.time() < end:
            if tab.eval("!!document.querySelector(%s)" % json.dumps(rest[0])):
                print("found")
                return
            time.sleep(0.3)
        print("TIMEOUT")
    else:
        raise SystemExit("unknown action: %s" % action)


if __name__ == "__main__":
    main()
