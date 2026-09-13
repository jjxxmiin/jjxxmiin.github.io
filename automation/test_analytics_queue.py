"""Execute the template bootstrap: reader events must work before network load."""
from pathlib import Path
import re
import subprocess


def test_reader_events_reach_global_queue_before_dom_ready():
    template = (Path(__file__).resolve().parents[1] / "_includes/analytics/google.html").read_text()
    script = re.search(r"<script>(.*?)</script>", template, re.S).group(1)
    subprocess.run(["node", "-e", """
const vm = require('node:vm');
const assert = require('node:assert/strict');
const context = {window: {dataLayer: [['existing']]}};
vm.createContext(context);
vm.runInContext(process.argv[1], context);
assert.equal(typeof context.window.gtag, 'function');
context.window.gtag('event', 'book_open', {book_path: '/posts/example/'});
assert.equal(context.window.dataLayer[0][0], 'existing');
const last = context.window.dataLayer.at(-1);
assert.equal(last[0], 'event');
assert.equal(last[1], 'book_open');
assert.equal(last[2].book_path, '/posts/example/');
""", script], check=True)
