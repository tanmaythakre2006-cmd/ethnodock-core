import re
import urllib.parse

def test_unicode():
    s = "芒果 (芒果) \u3000"
    print(repr(s))
    s_cleaned = re.sub(r'^\s+|\s+$', '', s, flags=re.UNICODE).title()
    print(repr(s_cleaned))

test_unicode()
