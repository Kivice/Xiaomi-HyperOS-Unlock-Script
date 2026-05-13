import hashlib
import random
import time
import json
import urllib3
import concurrent.futures
from datetime import datetime, timezone, timedelta
import ntplib
import pytz
from colorama import init, Fore, Style

init(autoreset=True)
col_g = Fore.GREEN
col_gb = Style.BRIGHT + Fore.GREEN
col_b = Fore.BLUE
col_bb = Style.BRIGHT + Fore.BLUE
col_y = Fore.YELLOW
col_yb = Style.BRIGHT + Fore.YELLOW
col_r = Fore.RED
col_rb = Style.BRIGHT + Fore.RED

# -------- CONFIGURATION --------
FEED_TIME_MS = 350 # Starts 350ms before midnight to slide right behind the crash
BURST_COUNT = 8 # 8 shots to create a tighter net
STAGGER_MS = 75 # 75ms delay between shots to blanket the sweet spot
# -------------------------------

# Using Chinese NTP servers for exact sync with Xiaomi
ntp_servers = [
 "ntp.aliyun.com",
 "ntp1.aliyun.com",
 "ntp.tencent.com",
 "time.asia.apple.com"
]

def generate_device_id():
 random_data = f"{random.random()}-{time.time()}"
 return hashlib.sha1(random_data.encode('utf-8')).hexdigest().upper()

def get_initial_beijing_time():
 client = ntplib.NTPClient()
 beijing_tz = pytz.timezone("Asia/Shanghai")
 for server in ntp_servers:
 try:
 print(col_y + f"\nGetting Beijing time from {server} 🇨🇳" + Fore.RESET)
 response = client.request(server, version=3)
 ntp_time = datetime.fromtimestamp(response.tx_time, timezone.utc)
 beijing_time = ntp_time.astimezone(beijing_tz)
 print(col_g + f"[⏰🇨🇳]: " + Fore.RESET + f"{beijing_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")
 return beijing_time
 except Exception as e:
 print(col_r + f"Error connecting to {server}" + Fore.RESET)
 print(col_r + f"NTP Server Not Found. Check VPS connection." + Fore.RESET)
 return None

def get_synchronized_beijing_time(start_beijing_time, start_timestamp):
 elapsed = time.time() - start_timestamp
 return start_beijing_time + timedelta(seconds=elapsed)

class HTTP11Session:
 def __init__(self, pool_size=10):
 self.http = urllib3.PoolManager(
 maxsize=pool_size,
 retries=False,
 timeout=urllib3.Timeout(connect=2.0, read=5.0),
 headers={}
 )

 def make_request(self, method, url, headers=None, body=None):
 try:
 request_headers = {}
 if headers:
 request_headers.update(headers)
 request_headers['Content-Type'] = 'application/json; charset=utf-8'

 if method == 'POST':
 if body is None:
 body = '{"is_retry":true}'.encode('utf-8')
 request_headers['Content-Length'] = str(len(body))
 request_headers['Accept-Encoding'] = 'gzip, deflate, br'
 request_headers['User-Agent'] = 'okhttp/4.12.0'
 request_headers['Connection'] = 'keep-alive'

 return self.http.request(
 method,
 url,
 headers=request_headers,
 body=body,
 preload_content=True
 )
 except Exception as e:
 return None

def check_unlock_status(session, cookie_value, device_id):
 try:
 url = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
 headers = {
 "Cookie": f"new_bbs_serviceToken={cookie_value};versionCode=500411;versionName=5.4.11;deviceId={device_id};"
 }

 response = session.make_request('GET', url, headers=headers)
 if response is None:
 print(f"[Error] Could not retrieve unlock status.")
 return False

 response_data = json.loads(response.data.decode('utf-8'))

 if response_data.get("code") == 100004:
 print(col_r + f"[Error] Expired Cookie ... try again." + Fore.RESET)
 exit()

 data = response_data.get("data", {})
 is_pass = data.get("is_pass")
 button_state = data.get("button_state")
 deadline_format = data.get("deadline_format", "")

 if is_pass == 4:
 if button_state == 1:
 print(col_g + f"[Account Status]: " + Fore.RESET + f"Ready. Requests will be sent.")
 return True
 elif button_state == 2:
 print(col_y + f"[Account Status]: Blocked until {deadline_format}." + Fore.RESET)
 if input(col_b + "Continue anyway (Yes/No)? " + Fore.RESET).lower() in ['y', 'yes']: return True
 exit()
 elif is_pass == 1:
 print(col_g + f"[Account Status]: Request approved, unblock until {deadline_format}." + Fore.RESET)
 exit()
 return False
 except Exception as e:
 print(f"[Status Check Error] {e}")
 return False

def fire_single_shot(session, url, headers, start_beijing_time, start_timestamp, index):
 # Calculate the stagger delay based on thread index
 stagger_delay = index * (STAGGER_MS / 1000.0)
 if stagger_delay > 0:
 time.sleep(stagger_delay)

 req_time = get_synchronized_beijing_time(start_beijing_time, start_timestamp)
 print(col_yb + f"[Sent - Shot {index+1}]: " + Fore.RESET + f"{req_time.strftime('%H:%M:%S.%f')}")

 response = session.make_request('POST', url, headers=headers)

 resp_time = get_synchronized_beijing_time(start_beijing_time, start_timestamp)
 return response, resp_time, index

def main():
 print(col_b + "Insert below the value of cookie [new_bbs_serviceToken]" + Fore.RESET)
 cookie_value = input("new_bbs_serviceToken: ").strip()

 device_id = generate_device_id()
 session = HTTP11Session(pool_size=BURST_COUNT)

 print (col_y + f"\nChecking Account Status..." + Fore.RESET)
 if not check_unlock_status(session, cookie_value, device_id):
 exit()

 start_beijing_time = get_initial_beijing_time()
 if start_beijing_time is None:
 exit()

 start_timestamp = time.time()

 # Calculate Target
 next_day = start_beijing_time + timedelta(days=1)
 target_time = next_day.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(milliseconds=FEED_TIME_MS)

 print(col_g + f"\n[Phase Shift]: " + Fore.RESET + f"Starts {FEED_TIME_MS}ms early, staggered by {STAGGER_MS}ms")
 print(col_g + f"[Target Fire Time]: " + Fore.RESET + f"{target_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")

 url = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
 headers = {
 "Cookie": f"new_bbs_serviceToken={cookie_value};versionCode=500411;versionName=5.4.11;deviceId={device_id};",
 "Connection": "keep-alive"
 }

 warm_up_done = False

 # Wait Loop
 while True:
 current_time = get_synchronized_beijing_time(start_beijing_time, start_timestamp)
 time_diff = (target_time - current_time).total_seconds()

 # WARM UP: 8 seconds before target, send a dummy request to build SSL cache
 if time_diff < 8.0 and not warm_up_done:
 print(col_y + f"[Network] Pre-heating SSL connection for Azure routing..." + Fore.RESET)
 session.make_request('GET', "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state", headers=headers)
 warm_up_done = True

 if time_diff > 1:
 time.sleep(0.5)
 elif current_time >= target_time:
 break

 # THE STAGGERED BURST
 print(col_rb + f"\n[00:00:00 RESET DETECTED] FIRING {BURST_COUNT} STAGGERED REQUESTS!" + Fore.RESET)

 success_found = False
 with concurrent.futures.ThreadPoolExecutor(max_workers=BURST_COUNT) as executor:
 # Launch threads, passing the index to calculate stagger delay
 futures = [executor.submit(fire_single_shot, session, url, headers, start_beijing_time, start_timestamp, i) for i in range(BURST_COUNT)]

 for future in concurrent.futures.as_completed(futures):
 response, resp_time, index = future.result()

 if response is None:
 continue

 try:
 json_response = json.loads(response.data.decode('utf-8'))
 code = json_response.get("code")
 data = json_response.get("data", {})

 # Print response time
 print(col_g + f"[Received - Shot {index+1}]: " + Fore.RESET + f"{resp_time.strftime('%H:%M:%S.%f')} | Code: {code}")

 if code == 0 and not success_found:
 apply_result = data.get("apply_result")
 if apply_result == 1:
 print(col_gb + "\n[SUCCESS] Request approved!" + Fore.RESET)
 success_found = True
 elif apply_result == 3:
 print(col_r + f"[Quota Reached] Try again at {data.get('deadline_format')}." + Fore.RESET)
 elif apply_result == 4:
 print(col_r + f"[Blocked] Account blocked until {data.get('deadline_format')}." + Fore.RESET)
 success_found = True

 except json.JSONDecodeError:
 pass
 except Exception as e:
 pass

 print(col_b + "\n[Execution Finished] Check logs above." + Fore.RESET)

if __name__ == "__main__":
 main()
