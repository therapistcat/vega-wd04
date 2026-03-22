import urllib.request
import urllib.parse

prompts = ["earthquake safety drop cover hold", "fire safety crawl exit", "flood safety high ground"]
for i, p in enumerate(prompts):
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p)}?width=1024&height=768&nologo=true"
    print(f"Fetching {i}: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            with open(f"test_poll_{i}.jpg", "wb") as f:
                f.write(data)
            print(f"SUCCESS {i}, size: {len(data)}")
    except Exception as e:
        print(f"FAILED {i}: {e}")
