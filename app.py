from flask import Flask, render_template_string, request, jsonify
import requests
import hashlib
import random
import time
import os

app = Flask(__name__)

HTML_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>IPKO Image Fetch</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { width: 100%; padding: 12px; background: #d32f2f; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        button:hover { background: #b71c1c; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        #result { margin-top: 20px; text-align: center; }
        #result img { max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }
        .error { color: #d32f2f; margin-top: 10px; white-space: pre-wrap; text-align: left; font-size: 12px; }
        .loading { color: #666; }
        .info { font-size: 12px; color: #666; margin-top: 10px; word-break: break-all; }
        .debug { background: #f0f0f0; padding: 10px; border-radius: 4px; margin-top: 10px; text-align: left; font-size: 11px; font-family: monospace; max-height: 300px; overflow: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h2>IPKO Safety Image</h2>
        <input type="text" id="login" placeholder="Login" value="75363350">
        <button onclick="fetchImage()" id="btn">Fetch Image</button>
        <div id="result"></div>
    </div>

    <script>
        async function fetchImage() {
            const login = document.getElementById("login").value;
            const result = document.getElementById("result");
            const btn = document.getElementById("btn");
            
            btn.disabled = true;
            btn.textContent = "Loading...";
            result.innerHTML = '<p class="loading">Fetching...</p>';

            try {
                const res = await fetch("/fetch", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({login: login})
                });
                
                const data = await res.json();
                
                if (data.success && data.image) {
                    result.innerHTML = `
                        <img src="${data.image}" alt="Safety Image">
                        <p class="info">Tracking: ${data.tracking || 'N/A'}</p>
                    `;
                } else if (data.raw) {
                    result.innerHTML = `
                        <p class="error">No image in response. Raw response:</p>
                        <div class="debug">${JSON.stringify(data.raw, null, 2)}</div>
                    `;
                } else {
                    result.innerHTML = `<p class="error">Error: ${data.error || 'Unknown'}</p>`;
                }
            } catch (err) {
                result.innerHTML = `<p class="error">Failed: ${err.message}</p>`;
            }
            
            btn.disabled = false;
            btn.textContent = "Fetch Image";
        }
    </script>
</body>
</html>
'''

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/fetch", methods=["POST"])
def fetch():
    data = request.get_json()
    login = data.get("login", "75363350")
    
    fp = hashlib.md5(f"{login}{time.time()}{random.random()}".encode()).hexdigest()
    
    payload = {
        "version": 3,
        "seq": 0,
        "location": "",
        "state_id": "login",
        "data": {
            "login": login,
            "fingerprint": fp
        },
        "action": "submit"
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://www.ipko.pl",
        "Referer": "https://www.ipko.pl/ipko3/login",
        "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "X-Requested-With": "XMLHttpRequest",
    }
    
    try:
        s = requests.Session()
        
        # First GET
        get_resp = s.get(
            "https://www.ipko.pl/ipko3/login",
            headers={**headers, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"},
            timeout=15,
            allow_redirects=True
        )
        
        time.sleep(0.5)
        
        # POST
        post_resp = s.post(
            "https://www.ipko.pl/ipko3/login",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        resp = post_resp.json()
        
        # Debug: log the full response structure
        print("FULL RESPONSE:", resp)
        
        img = resp.get("data", {}).get("image", {}).get("src", "")
        track = resp.get("data", {}).get("tracking_pixel", "")
        
        if not img:
            # Return raw response for debugging
            return jsonify({
                "success": False,
                "raw": resp,
                "status_code": post_resp.status_code,
                "error": "No image in response"
            })
        
        return jsonify({
            "success": True,
            "image": img,
            "tracking": track
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
